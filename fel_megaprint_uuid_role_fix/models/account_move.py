# -*- coding: utf-8 -*-
import base64
import html
import logging
import time
import uuid

import requests
from lxml import etree

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    # ------------------------------------------------------------------
    # Request IDs
    # ------------------------------------------------------------------
    def _megaprint_cert_base_request_id(self):
        """Legacy id used by the old module for both certification and annulment."""
        self.ensure_one()
        return str(uuid.uuid5(uuid.NAMESPACE_OID, str(self.id))).upper()

    def _megaprint_cert_request_id(self):
        """Stable id used only for certification.

        This intentionally differs from the legacy id so that a DTE cannot
        collide with a previous annulment XML that was registered using the
        same old uuid5(account.move.id) formula.
        """
        self.ensure_one()
        seed = "account.move:%s:fel:cert:v2" % self.id
        return str(uuid.uuid5(uuid.NAMESPACE_OID, seed)).upper()

    # ------------------------------------------------------------------
    # XML helpers
    # ------------------------------------------------------------------
    def _megaprint_xml_node_to_text(self, node):
        if node is None:
            return ""
        text = (node.text or "").strip()
        if text:
            return text
        try:
            return "".join(etree.tostring(child, encoding="unicode") for child in node)
        except Exception:
            return ""

    def _megaprint_normalize_xml_text(self, xml_text):
        xml_text = xml_text or ""
        if isinstance(xml_text, bytes):
            xml_text = xml_text.decode("utf-8", errors="ignore")
        xml_text = xml_text.strip()
        for _i in range(3):
            unescaped = html.unescape(xml_text).strip()
            if unescaped == xml_text:
                break
            xml_text = unescaped
        return xml_text

    def _megaprint_xml_dte_kind(self, xml_text):
        """Return 'dte', 'annulment', 'empty', or 'unknown'."""
        text = self._megaprint_normalize_xml_text(xml_text)
        if not text:
            return "empty"
        if "GTAnulacionDocumento" in text or "AnulacionDTE" in text or "NumeroDocumentoAAnular" in text:
            return "annulment"
        if "GTDocumento" in text or "NumeroAutorizacion" in text:
            return "dte"
        try:
            root = etree.XML(text.encode("utf-8"))
            root_name = etree.QName(root).localname
            if root_name == "GTAnulacionDocumento":
                return "annulment"
            if root.xpath("//*[local-name()='AnulacionDTE']") or root.xpath("//*[@NumeroDocumentoAAnular]"):
                return "annulment"
            if root_name == "GTDocumento" or root.xpath("//*[local-name()='NumeroAutorizacion']"):
                return "dte"
        except Exception as exc:
            _logger.warning("[MEGAPRINT][UUID_ROLE_FIX] Could not classify xml_dte: %s", exc)
        return "unknown"


    def _megaprint_sanitize_dte_xml_before_sign(self, xml_text):
        """Sanitize the unsigned DTE before sending it to Megaprint for signature.

        This keeps the behavior of the installed sanitize module even when this
        module overrides certificar_megaprint() directly. It fixes a common FEL
        conflict where the base XML generator emits two IVA nodes for the same
        line: one generated as standard IVA with MontoImpuesto 0, and another
        generated from tax configuration tipo_impuesto_fel='IVA'. SAT/Megaprint
        then rejects the document with FEL_SEC_500/FEL_RCP32 and often FEL_RCP36.
        """
        self.ensure_one()
        if not xml_text:
            return xml_text

        ns = {"dte": "http://www.sat.gob.gt/dte/fel/0.2.0"}
        try:
            root = etree.fromstring(xml_text.encode("utf-8"), parser=etree.XMLParser(remove_blank_text=True))

            changed = False

            # 1) Remove exento/no afecto phrase generated only because the default
            # zero-IVA node made the invoice look like it had untaxed lines.
            for frase in root.xpath(".//dte:Frase[@TipoFrase='4']", namespaces=ns):
                parent = frase.getparent()
                if parent is not None:
                    parent.remove(frase)
                    changed = True

            # 2) Remove IVA/other tax nodes with amount 0 inside each item.
            # This is intentionally conservative: only zero tax rows are removed;
            # positive rows produced by Odoo tax computation are kept.
            for imp in root.xpath(".//dte:Item/dte:Impuestos/dte:Impuesto", namespaces=ns):
                monto_node = imp.find("dte:MontoImpuesto", namespaces=ns)
                try:
                    amount = float(((monto_node.text if monto_node is not None else "0") or "0").strip())
                except Exception:
                    amount = 0.0
                if abs(amount) < 0.0000005:
                    parent = imp.getparent()
                    if parent is not None:
                        parent.remove(imp)
                        changed = True

            # 3) Remove empty <Impuestos> containers left after removing zero rows.
            for impuestos in root.xpath(".//dte:Item/dte:Impuestos", namespaces=ns):
                if len(impuestos) == 0:
                    parent = impuestos.getparent()
                    if parent is not None:
                        parent.remove(impuestos)
                        changed = True

            # 4) Remove zero totals, especially duplicate TotalImpuesto IVA=0.
            for total_imp in root.xpath(".//dte:Totales/dte:TotalImpuestos/dte:TotalImpuesto", namespaces=ns):
                try:
                    amount = float((total_imp.get("TotalMontoImpuesto") or "0").strip())
                except Exception:
                    amount = 0.0
                if abs(amount) < 0.0000005:
                    parent = total_imp.getparent()
                    if parent is not None:
                        parent.remove(total_imp)
                        changed = True

            # 5) Remove empty TotalImpuestos container if all totals disappeared.
            for total_impuestos in root.xpath(".//dte:Totales/dte:TotalImpuestos", namespaces=ns):
                if len(total_impuestos) == 0:
                    parent = total_impuestos.getparent()
                    if parent is not None:
                        parent.remove(total_impuestos)
                        changed = True

            # 6) Normalize unit measure text to match old sanitize behavior.
            for um in root.xpath(".//dte:Item/dte:UnidadMedida", namespaces=ns):
                if um.text:
                    new_text = str(um.text).strip().upper()
                    if new_text != um.text:
                        um.text = new_text
                        changed = True

            if changed:
                _logger.warning(
                    "[MEGAPRINT][UUID_ROLE_FIX] XML DTE saneado antes de firma: "
                    "se removieron impuestos/totales en cero y Frase TipoFrase=4 si aplicaba."
                )
            return etree.tostring(root, encoding="utf-8", xml_declaration=False).decode("utf-8")
        except Exception as exc:
            _logger.warning("[MEGAPRINT][UUID_ROLE_FIX] No se pudo sanear XML DTE antes de firma: %s", exc)
            return xml_text

    def _megaprint_extract_errors(self, resultado_xml):
        errors = []
        try:
            for e in resultado_xml.xpath("//listado_errores//descripcion_errores | //descripcion_errores"):
                if e is not None and (e.text or "").strip():
                    errors.append(e.text.strip())
        except Exception:
            pass
        return errors

    def _megaprint_api_hosts(self):
        self.ensure_one()
        request_url = "apiv2"
        request_path = ""
        request_url_firma = ""
        if getattr(self.company_id, "pruebas_fel", False):
            request_url = "dev2.api"
            request_path = ""
            request_url_firma = "dev."
        return request_url, request_path, request_url_firma

    def _megaprint_get_token_headers(self, request_url, request_path):
        self.ensure_one()
        headers = {"Content-Type": "application/xml"}
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<SolicitaTokenRequest><usuario>%s</usuario><apikey>%s</apikey></SolicitaTokenRequest>'
        ) % (self.journal_id.usuario_fel, self.journal_id.clave_fel)
        r = requests.post(
            'https://%s.ifacere-fel.com/%sapi/solicitarToken' % (request_url, request_path),
            data=data.encode('utf-8'),
            headers=headers,
            timeout=(5, 30),
        )
        resultado_xml = etree.XML(r.text.encode('utf-8'))
        if not resultado_xml.xpath("//token"):
            raise UserError(r.text)
        token = resultado_xml.xpath("//token")[0].text
        return {"Content-Type": "application/xml", "authorization": "Bearer " + token}

    def _megaprint_verificar_xml_dte_by_request_id(self, api_host, request_path, headers, request_id):
        vdata = '<?xml version="1.0" encoding="UTF-8"?><VerificaDocumentoRequest id="%s"/>' % request_id
        rv = requests.post(
            'https://%s.ifacere-fel.com/%sapi/verificarDocumento' % (api_host, request_path),
            data=vdata.encode('utf-8'),
            headers=headers,
            timeout=(5, 12),
        )
        vxml = etree.XML(rv.text.encode('utf-8'))
        vnode = vxml.xpath("//xml_dte")
        xml_dte = self._megaprint_xml_node_to_text(vnode[0]) if vnode else ""
        uuid_dte = (vxml.findtext(".//uuid") or "").strip()
        return xml_dte, uuid_dte, vxml

    def _megaprint_retornar_xml_by_uuid(self, api_host, request_path, headers, uuid_dte):
        if not uuid_dte:
            return ""
        rx = '<?xml version="1.0" encoding="UTF-8"?><RetornaXMLRequest><uuid>%s</uuid></RetornaXMLRequest>' % uuid_dte
        rr = requests.post(
            'https://%s.ifacere-fel.com/%sapi/retornarXML' % (api_host, request_path),
            data=rx.encode('utf-8'),
            headers=headers,
            timeout=(5, 15),
        )
        rxml = etree.XML(rr.text.encode('utf-8'))
        vnode = rxml.xpath("//xml_dte")
        return self._megaprint_xml_node_to_text(vnode[0]) if vnode else ""

    def _megaprint_apply_if_normal_dte(self, xml_dte, source_label):
        """Apply the FEL info if xml_dte is a normal DTE. Return True if applied."""
        self.ensure_one()
        if not xml_dte:
            return False
        kind = self._megaprint_xml_dte_kind(xml_dte)
        if kind == "dte":
            if self._fel_apply_from_xml(self, xml_dte):
                self._fel_sync_from_name_if_needed(self)
                _logger.info("[MEGAPRINT][UUID_ROLE_FIX] Applied normal DTE from %s for move %s", source_label, self.id)
                return True
            raise UserError(
                "Megaprint devolvió xml_dte de factura desde %s, pero no se pudo aplicar NumeroAutorizacion."
                % source_label
            )
        if kind == "annulment":
            _logger.warning(
                "[MEGAPRINT][UUID_ROLE_FIX] %s returned annulment XML for move %s; it will not be applied as invoice.",
                source_label, self.id,
            )
        return False

    def _megaprint_sign_register_and_recover(self, request_url, request_path, request_url_firma, headers, request_id, xml_sin_firma):
        self.ensure_one()

        # Firmar
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<FirmaDocumentoRequest id="%s"><xml_dte><![CDATA[%s]]></xml_dte></FirmaDocumentoRequest>'
        ) % (request_id, xml_sin_firma)
        r = requests.post(
            'https://%sapi.soluciones-mega.com/api/solicitaFirma' % request_url_firma,
            data=data.encode('utf-8'),
            headers=headers,
            timeout=(5, 30),
        )
        resultado_xml = etree.XML(r.text.encode('utf-8'))
        if not resultado_xml.xpath("//xml_dte"):
            raise UserError(r.text)
        xml_con_firma = self._megaprint_xml_node_to_text(resultado_xml.xpath("//xml_dte")[0])

        if hasattr(self, 'documento_xml_fel'):
            try:
                self.documento_xml_fel = base64.b64encode(xml_con_firma.encode('utf-8'))
            except Exception:
                pass

        # Registrar
        data = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<RegistraDocumentoRequest id="%s"><xml_dte><![CDATA[%s]]></xml_dte></RegistraDocumentoRequest>'
        ) % (request_id, xml_con_firma)
        r = requests.post(
            'https://%s.ifacere-fel.com/%sapi/registrarDocumentoUuid' % (request_url, request_path),
            data=data.encode('utf-8'),
            headers=headers,
            timeout=(5, 30),
        )
        resultado_xml = etree.XML(r.text.encode('utf-8'))

        if hasattr(self, 'resultado_xml_fel'):
            try:
                self.resultado_xml_fel = base64.b64encode(etree.tostring(resultado_xml))
            except Exception:
                pass

        xml_certificado = ""
        node = resultado_xml.xpath("//xml_dte")
        if node:
            xml_certificado = self._megaprint_xml_node_to_text(node[0])

        t0 = time.time()
        while not xml_certificado and time.time() - t0 < 10:
            try:
                xml_from_id, uuid_dte, _vxml = self._megaprint_verificar_xml_dte_by_request_id(
                    request_url, request_path, headers, request_id
                )
                if xml_from_id:
                    xml_certificado = xml_from_id
                    break
                if uuid_dte:
                    xml_from_uuid = self._megaprint_retornar_xml_by_uuid(request_url, request_path, headers, uuid_dte)
                    if xml_from_uuid:
                        xml_certificado = xml_from_uuid
                        break
            except Exception as exc:
                _logger.warning("[MEGAPRINT][UUID_ROLE_FIX] recuperación rápida falló para id=%s: %s", request_id, exc)
            time.sleep(1)

        return xml_certificado, resultado_xml

    # ------------------------------------------------------------------
    # Main flow override
    # ------------------------------------------------------------------
    def certificar_megaprint(self):
        _logger.warning('[MEGAPRINT][UUID_ROLE_FIX 18.0.1.0.2] Ejecutando certificar_megaprint')

        for factura in self:
            if not getattr(factura.journal_id, 'usuario_fel', False):
                continue

            if getattr(factura, 'firma_fel', False):
                raise UserError("La factura ya fue validada, por lo que no puede ser validada nuevamente")

            dte = factura.dte_documento()
            if dte is None:
                continue

            xml_sin_firma = etree.tostring(dte, encoding="UTF-8").decode("utf-8")
            xml_sin_firma = factura._megaprint_sanitize_dte_xml_before_sign(xml_sin_firma)
            request_url, request_path, request_url_firma = factura._megaprint_api_hosts()
            headers = factura._megaprint_get_token_headers(request_url, request_path)

            legacy_id = factura._megaprint_cert_base_request_id()
            cert_id = factura._megaprint_cert_request_id()

            # 1) If legacy id already has a normal DTE, apply it and stop.
            #    If it has an annulment XML or cannot return a normal DTE, do NOT reuse it for certification.
            try:
                legacy_xml, legacy_uuid, _legacy_vxml = factura._megaprint_verificar_xml_dte_by_request_id(
                    request_url, request_path, headers, legacy_id
                )
                if factura._megaprint_apply_if_normal_dte(legacy_xml, "legacy id %s" % legacy_id):
                    continue
                if legacy_uuid and not legacy_xml:
                    legacy_xml_by_uuid = factura._megaprint_retornar_xml_by_uuid(
                        request_url, request_path, headers, legacy_uuid
                    )
                    if factura._megaprint_apply_if_normal_dte(
                        legacy_xml_by_uuid, "legacy uuid %s / id %s" % (legacy_uuid, legacy_id)
                    ):
                        continue
                _logger.warning(
                    "[MEGAPRINT][UUID_ROLE_FIX] Legacy id %s no contiene factura aplicable. "
                    "Usando certification-only id %s para move %s.",
                    legacy_id, cert_id, factura.id,
                )
            except Exception as exc:
                _logger.warning(
                    "[MEGAPRINT][UUID_ROLE_FIX] No se pudo usar/preverificar legacy id %s: %s. "
                    "Usando certification-only id %s.",
                    legacy_id, exc, cert_id,
                )

            # 2) Certification-only id is the only id we use for a new certification.
            #    Precheck it first to keep retries idempotent.
            try:
                cert_xml, cert_uuid, _cert_vxml = factura._megaprint_verificar_xml_dte_by_request_id(
                    request_url, request_path, headers, cert_id
                )
                if factura._megaprint_apply_if_normal_dte(cert_xml, "certification id %s" % cert_id):
                    continue
                if cert_uuid and not cert_xml:
                    cert_xml_by_uuid = factura._megaprint_retornar_xml_by_uuid(request_url, request_path, headers, cert_uuid)
                    if factura._megaprint_apply_if_normal_dte(
                        cert_xml_by_uuid, "certification uuid %s / id %s" % (cert_uuid, cert_id)
                    ):
                        continue
                    if factura._megaprint_xml_dte_kind(cert_xml_by_uuid) == "annulment":
                        raise UserError(
                            "El ID de certificación %s ya devuelve XML de anulación. No se reenvió para evitar inconsistencias."
                            % cert_id
                        )
            except UserError:
                raise
            except Exception as exc:
                _logger.warning("[MEGAPRINT][UUID_ROLE_FIX] Precheck de cert_id %s falló: %s", cert_id, exc)

            # 3) Sign/register with certification-only id.
            xml_certificado, resultado_xml = factura._megaprint_sign_register_and_recover(
                request_url, request_path, request_url_firma, headers, cert_id, xml_sin_firma
            )

            if xml_certificado:
                kind = factura._megaprint_xml_dte_kind(xml_certificado)
                if kind == "annulment":
                    raise UserError(
                        "Megaprint devolvió XML de anulación incluso usando el ID exclusivo de certificación. "
                        "No se aplicó como factura. ID certificación=%s." % cert_id
                    )
                if factura._fel_apply_from_xml(factura, xml_certificado):
                    factura._fel_sync_from_name_if_needed(factura)
                    continue
                raise UserError("No se pudo aplicar NumeroAutorizacion del xml_dte (id=%s)." % cert_id)

            # 4) No XML received: show provider errors if present.
            msg = (
                "No se recibió xml_dte del certificador para id=%s; "
                "no se reenvió para evitar duplicados."
            ) % cert_id
            try:
                tipo_resp = (resultado_xml.findtext(".//tipo_respuesta") or "").strip()
            except Exception:
                tipo_resp = ""
            errores = factura._megaprint_extract_errors(resultado_xml)
            if tipo_resp and tipo_resp != "0":
                if errores:
                    msg = "Error FEL (tipo_respuesta=%s) para id=%s:\n%s" % (
                        tipo_resp, cert_id, "\n".join(errores)
                    )
                else:
                    msg = "Error FEL sin xml_dte (tipo_respuesta=%s) para id=%s.\nXML:\n%s" % (
                        tipo_resp, cert_id, etree.tostring(resultado_xml, encoding="unicode")
                    )
            raise UserError(msg)

        return True
