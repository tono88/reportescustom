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

            # === Credenciales desde el DIARIO (alineado con tu módulo actual) ===
            j = move.journal_id
            if not j:
                raise UserError(_("La factura no tiene diario asignado."))

            usuario = _pick(self, j, ['usuario_fel', 'fel_usuario', 'fel_user', 'user_fel'])
            clave   = _pick(self, j, ['clave_fel', 'fel_clave', 'fel_password', 'password_fel'])
            modo    = _pick(self, j, ['pruebas_fel', 'fel_pruebas', 'fel_environment'])

            if not usuario or not clave:
                raise UserError(_("Configure Usuario/Clave FEL en el Diario de la factura."))

            is_test = False
            if isinstance(modo, bool):
                is_test = modo
            elif isinstance(modo, str):
                is_test = modo.lower() in ('test','pruebas','sandbox','dev','development')

            # === Construir XML de anulación usando tu helper existente ===
            if not hasattr(move, "dte_anulacion"):
                raise UserError(_("No se encontró dte_anulacion() en el modelo; verifique fel_gt/fel_megaprint."))
            dte = move.dte_anulacion()
            xml_sin_firma = etree.tostring(dte, encoding="UTF-8").decode("utf-8")

            # === Endpoints Megaprint (coinciden con 17.x) ===
            api_host   = "dev2.api.ifacere-fel.com" if is_test else "apiv2.ifacere-fel.com"
            firma_host = "dev.ifacere-firma.com"    if is_test else "ifacere-firma.com"

            # 1) Token (corrección: SolicitaTokenRequest + /api/solicitaToken)
            headers_xml = {"Content-Type": "application/xml"}
            payload = '<?xml version="1.0" encoding="UTF-8"?><SolicitaTokenRequest id="{0}"><usuario>{1}</usuario><clave>{2}</clave></SolicitaTokenRequest>'.format(
                uuid.uuid4().hex, usuario, clave
            )
            r = requests.post('https://{}/api/solicitaToken'.format(api_host), data=payload, headers=headers_xml, timeout=60)
            try:
                token_xml = etree.XML(r.text.encode('utf-8'))
            except Exception:
                _logger.exception("TokenResponse inválida: %s", r.text)
                raise UserError(_("No se pudo solicitar token a Megaprint.\nRespuesta cruda:\n%s") % r.text)
            token_nodes = token_xml.xpath("//token")
            if not token_nodes or not token_nodes[0].text:
                raise UserError(_("Megaprint no devolvió token.\nRespuesta:\n%s") % r.text)
            token = token_nodes[0].text

            # 2) Firma
            headers_auth = {"Content-Type": "application/xml", "authorization": "Bearer " + token}
            req_id = str(uuid.uuid5(uuid.NAMESPACE_OID, str(move.id))).upper()
            sign_payload = '<?xml version="1.0" encoding="UTF-8"?><FirmaDocumentoRequest id="{0}"><xml_dte><![CDATA[{1}]]></xml_dte></FirmaDocumentoRequest>'.format(
                req_id, xml_sin_firma
            )
            r = requests.post('https://{}/api/solicitaFirma'.format(firma_host), data=sign_payload.encode('utf-8'), headers=headers_auth, timeout=60)
            try:
                sign_xml = etree.XML(r.text.encode('utf-8'))
            except Exception:
                _logger.exception("FirmaResponse inválida: %s", r.text)
                raise UserError(_("Error al firmar XML de anulación.\nRespuesta cruda:\n%s") % r.text)

            signed_nodes = sign_xml.xpath("//xml_dte")
            if not signed_nodes or not signed_nodes[0].text:
                raise UserError(_("No se obtuvo xml_dte firmado.\nRespuesta:\n%s") % r.text)
            xml_firmado = html.unescape(signed_nodes[0].text)

            # 3) Anulación
            annul_payload = '<?xml version="1.0" encoding="UTF-8"?><AnulaDocumentoXMLRequest id="{0}"><xml_dte><![CDATA[{1}]]></xml_dte></AnulaDocumentoXMLRequest>'.format(
                req_id, xml_firmado
            )
            r = requests.post('https://{}/api/anularDocumentoXML'.format(api_host), data=annul_payload.encode('utf-8'), headers=headers_auth, timeout=60)
            try:
                annul_xml = etree.XML(r.text.encode('utf-8'))
            except Exception:
                _logger.exception("AnulaResponse inválida: %s", r.text)
                raise UserError(_("Error al enviar anulación.\nRespuesta cruda:\n%s") % r.text)

            # Errores?
            if annul_xml.xpath("//listado_errores"):
                raise UserError(_("Megaprint devolvió errores:\n%s") % r.text)

            move.message_post(body=_("Anulación FEL solicitada a Megaprint.\nRespuesta:\n%s") % r.text)
        return True
