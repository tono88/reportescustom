# -*- encoding: utf-8 -*-
import logging, html, uuid
from odoo import models, _
from odoo.exceptions import UserError
from lxml import etree
import requests

_logger = logging.getLogger(__name__)

def _pick(model, rec, names):
    """Return first non-empty attribute from 'names' on record 'rec'."""
    for n in names:
        if hasattr(rec, n):
            val = getattr(rec, n)
            if isinstance(val, str):
                if val.strip():
                    return val.strip()
            elif val:
                return val
    return False

def _env_is_test(move, journal_flag):
    """
    Decide el modo pruebas:
      - Prioriza flag boolean o string del diario (como ya tenías).
      - Si la empresa tiene un boolean tipo 'pruebas_fel' / 'fel_pruebas', lo usa si no
        hay info en el diario.
    """
    is_test = False
    if isinstance(journal_flag, bool):
        is_test = journal_flag
    elif isinstance(journal_flag, str):
        is_test = journal_flag.lower() in ('test', 'pruebas', 'sandbox', 'dev', 'development')

    if not is_test and move.company_id:
        comp_flag = _pick(move, move.company_id, ['pruebas_fel', 'fel_pruebas'])
        if isinstance(comp_flag, bool):
            is_test = comp_flag
        elif isinstance(comp_flag, str):
            is_test = comp_flag.lower() in ('test', 'pruebas', 'sandbox', 'dev', 'development')
    return is_test

def _request_token(api_host, usuario, clave):
    """
    Igual que v17:
      - URL: https://{api_host}/api/solicitarToken   (con 'r' en la URL)
      - XML: <SolicitaTokenRequest>                  (sin 'r' en el tag)
    """
    headers_xml = {"Content-Type": "application/xml", "Accept": "application/xml"}
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<SolicitaTokenRequest id="{rid}"><usuario>{usr}</usuario><clave>{pwd}</clave></SolicitaTokenRequest>'
    ).format(rid=uuid.uuid4().hex, usr=usuario, pwd=clave)

    url = f'https://{api_host}/api/solicitarToken'
    r = requests.post(url, data=payload.encode("utf-8"), headers=headers_xml, timeout=60)
    if not (r.text or "").strip():
        raise UserError(_("No se pudo solicitar token a Megaprint.\nURL: %s\nHTTP: %s\nHeaders: %s\nRespuesta vacía") %
                        (url, r.status_code, dict(r.headers)))
    try:
        xml = etree.XML(r.text.encode("utf-8"))
    except Exception:
        _logger.exception("TokenResponse inválida (%s): %s", url, r.text)
        raise UserError(_("No se pudo solicitar token a Megaprint.\nURL: %s\nHTTP: %s\nRespuesta:\n%s") %
                        (url, r.status_code, r.text))

    nodes = xml.xpath("//token")
    if not nodes or not nodes[0].text:
        raise UserError(_("Megaprint no devolvió token.\nURL: %s\nHTTP: %s\nRespuesta:\n%s") %
                        (url, r.status_code, r.text))
    return nodes[0].text, url, r.text

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_annul_fel_megaprint(self):
        for move in self:
            # Sanity checks
            if not getattr(move, "requiere_certificacion", None):
                raise UserError(_("FEL no instalado correctamente: falta requiere_certificacion()."))
            if not move.requiere_certificacion():
                raise UserError(_("Este documento no requiere certificación FEL."))
            if not getattr(move, "firma_fel", None):
                raise UserError(_("La factura no posee firma FEL; no se puede anular."))

            # === Credenciales desde el DIARIO ===
            j = move.journal_id
            if not j:
                raise UserError(_("La factura no tiene diario asignado."))

            usuario = _pick(self, j, ['usuario_fel', 'fel_usuario', 'fel_user', 'user_fel'])
            clave   = _pick(self, j, ['clave_fel', 'fel_clave', 'fel_password', 'password_fel'])
            modo    = _pick(self, j, ['pruebas_fel', 'fel_pruebas', 'fel_environment'])

            if not usuario or not clave:
                raise UserError(_("Configure Usuario/Clave FEL en el Diario de la factura."))

            # === Endpoints Megaprint (prod/dev) ===
            is_test = _env_is_test(move, modo)
            api_host   = "dev2.api.ifacere-fel.com" if is_test else "apiv2.ifacere-fel.com"
            firma_host = ("dev." if is_test else "") + "api.soluciones-mega.com"

            # 1) Token (con estrategia multi-path + Accept: xml)
            token, token_url, raw_token_resp = _request_token(api_host, usuario, clave)
            _logger.info("Token FEL obtenido desde %s", token_url)

            # 2) Firma
            headers_auth = {"Content-Type": "application/xml", "authorization": "Bearer " + token, "Accept": "application/xml"}
            # XML de anulación
            if not hasattr(move, "dte_anulacion"):
                raise UserError(_("No se encontró dte_anulacion() en el modelo; verifique fel_gt/fel_megaprint."))
            dte = move.dte_anulacion()
            xml_sin_firma = etree.tostring(dte, encoding="UTF-8").decode("utf-8")

            req_id = str(uuid.uuid5(uuid.NAMESPACE_OID, str(move.id))).upper()
            sign_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<FirmaDocumentoRequest id="{rid}"><xml_dte><![CDATA[{xml}]]></xml_dte></FirmaDocumentoRequest>'
            ).format(rid=req_id, xml=xml_sin_firma)

            r = requests.post('https://{}/api/solicitaFirma'.format(firma_host), data=sign_payload.encode('utf-8'), headers=headers_auth, timeout=60)
            try:
                sign_xml = etree.XML((r.text or "").encode('utf-8'))
            except Exception:
                _logger.exception("FirmaResponse inválida: %s", r.text)
                raise UserError(_("Error al firmar XML de anulación.\nRespuesta cruda:\n%s") % (r.text or ""))

            signed_nodes = sign_xml.xpath("//xml_dte")
            if not signed_nodes or not signed_nodes[0].text:
                raise UserError(_("No se obtuvo xml_dte firmado.\nRespuesta:\n%s") % (r.text or ""))
            xml_firmado = html.unescape(signed_nodes[0].text)

            # 3) Anulación
            annul_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<AnulaDocumentoXMLRequest id="{rid}"><xml_dte><![CDATA[{xml}]]></xml_dte></AnulaDocumentoXMLRequest>'
            ).format(rid=req_id, xml=xml_firmado)

            r = requests.post('https://{}/api/anularDocumentoXML'.format(api_host), data=annul_payload.encode('utf-8'), headers=headers_auth, timeout=60)
            try:
                annul_xml = etree.XML((r.text or "").encode('utf-8'))
            except Exception:
                _logger.exception("AnulaResponse inválida: %s", r.text)
                raise UserError(_("Error al enviar anulación.\nRespuesta cruda:\n%s") % (r.text or ""))

            if annul_xml.xpath("//listado_errores"):
                # Devuelve el XML crudo completo para diagnóstico
                raise UserError(_("Megaprint devolvió errores:\n%s") % (r.text or ""))

            move.message_post(body=_("Anulación FEL solicitada a Megaprint.\nToken URL: %s\nRespuesta:\n%s") % (token_url, (r.text or "")))
        return True
