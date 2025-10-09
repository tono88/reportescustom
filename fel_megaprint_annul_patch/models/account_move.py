# -*- encoding: utf-8 -*-
import logging, html, uuid, base64, re
from odoo import models, _
from odoo.exceptions import UserError
from lxml import etree
import requests

_logger = logging.getLogger(__name__)

# ----------------- utilidades -----------------
def _pick(model, rec, names):
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
    is_test = False
    if isinstance(journal_flag, bool):
        is_test = journal_flag
    elif isinstance(journal_flag, str):
        is_test = journal_flag.lower() in ('test','pruebas','sandbox','dev','development')
    if not is_test and move.company_id:
        comp_flag = _pick(move, move.company_id, ['pruebas_fel', 'fel_pruebas'])
        if isinstance(comp_flag, bool):
            is_test = comp_flag
        elif isinstance(comp_flag, str):
            is_test = comp_flag.lower() in ('test','pruebas','sandbox','dev','development')
    return is_test

def _get_creds(move):
    j = move.journal_id
    usuario = _pick(move, j, ['usuario_fel','fel_usuario','fel_user','user_fel']) if j else False
    apikey  = _pick(move, j, ['clave_fel','fel_clave','fel_password','password_fel']) if j else False
    modo    = _pick(move, j, ['pruebas_fel','fel_pruebas','fel_environment']) if j else None
    if (not usuario or not apikey) and move.company_id:
        c = move.company_id
        usuario = usuario or _pick(move, c, ['usuario_fel'])
        apikey  = apikey  or _pick(move, c, ['clave_fel'])
    if not usuario or not apikey:
        raise UserError(_("Configure Usuario y API Key FEL en el Diario o en la Compañía."))
    return usuario, apikey, modo

def _request_token(api_host, usuario, apikey):
    headers_xml = {"Content-Type":"application/xml", "Accept":"application/xml"}
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<SolicitaTokenRequest><usuario>{u}</usuario><apikey>{k}</apikey></SolicitaTokenRequest>'
    ).format(u=usuario, k=apikey)
    url = f'https://{api_host}/api/solicitarToken'
    r = requests.post(url, data=payload.encode("utf-8"), headers=headers_xml, timeout=60)
    if not (r.text or "").strip():
        raise UserError(_("No se pudo solicitar token a Megaprint.\nURL: %s\nHTTP: %s\nRespuesta vacía") % (url, r.status_code))
    try:
        xml = etree.XML(r.text.encode("utf-8"))
    except Exception:
        _logger.exception("TokenResponse inválida (%s): %s", url, r.text)
        raise UserError(_("No se pudo solicitar token a Megaprint.\nURL: %s\nHTTP: %s\nRespuesta:\n%s") % (url, r.status_code, r.text))
    nodes = xml.xpath("//token")
    if not nodes or not nodes[0].text:
        raise UserError(_("Megaprint no devolvió token.\nURL: %s\nHTTP: %s\nRespuesta:\n%s") % (url, r.status_code, r.text))
    return nodes[0].text, url, r.text

def _retornar_xml(api_host, token, uuid_val):
    """Plan B para recuperar el xml_dte de la certificación."""
    headers = {"Content-Type":"application/xml","Accept":"application/xml","authorization":"Bearer "+token}
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<RetornarXMLRequest><uuid>{u}</uuid></RetornarXMLRequest>'
    ).format(u=uuid_val)
    url = f'https://{api_host}/api/retornarXML'
    r = requests.post(url, data=payload.encode('utf-8'), headers=headers, timeout=60)
    try:
        xml = etree.XML((r.text or "").encode('utf-8'))
        node = xml.xpath('//xml_dte')
        if node and node[0].text:
            return html.unescape(node[0].text)
    except Exception:
        _logger.exception("No se pudo interpretar retornarXML: %s", r.text)
    return None

def _retornar_pdf_v2(api_host, token, uuid_val, xml_dte_text=None):
    """
    Retorna el PDF desde Megaprint. Intenta primero con el payload mínimo:
        <RetornaPDFRequest><uuid>...</uuid></RetornaPDFRequest>
    Si no hay PDF, reintenta con <uuid> y <xml_dte> (en ese orden).
    """
    headers = {"Content-Type":"application/xml", "Accept":"application/xml", "authorization":"Bearer "+token}
    url = f'https://{api_host}/api/retornarPDF'

    def _send_and_parse(payload):
        r = requests.post(url, data=payload.encode('utf-8'), headers=headers, timeout=60)
        try:
            xml = etree.XML((r.text or "").encode('utf-8'))
            pdf_node = xml.xpath('//pdf | //PDF')
            if pdf_node and (pdf_node[0].text or '').strip():
                return base64.b64decode(pdf_node[0].text)
            if xml.xpath('//listado_errores'):
                _logger.warning("retornarPDF devolvió errores: %s", r.text)
        except Exception:
            _logger.exception("retornarPDF no interpretable: %s", r.text)
        return None

    # 1) MÍNIMO: solo UUID
    payload_min = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<RetornaPDFRequest><uuid>{u}</uuid></RetornaPDFRequest>'
    ).format(u=uuid_val)
    pdf = _send_and_parse(payload_min)
    if pdf:
        return pdf

    # 2) Reintento con xml_dte si lo tenemos (o lo pedimos)
    if not xml_dte_text:
        xml_dte_text = _retornar_xml(api_host, token, uuid_val)
    if xml_dte_text:
        payload_full = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<RetornaPDFRequest><uuid>{u}</uuid><xml_dte><![CDATA[{xml}]]></xml_dte></RetornaPDFRequest>'
        ).format(u=uuid_val, xml=xml_dte_text)
        pdf = _send_and_parse(payload_full)

    return pdf or None

def _extract_annul_uuid_from_chatter(move):
    """Busca en chatter un 'UUID de anulación: XXXXX-...' para usarlo como plan B."""
    MM = move.env['mail.message'].sudo()
    msgs = MM.search([('model','=','account.move'),('res_id','=',move.id)], order='id desc', limit=15)
    pat = re.compile(r'UUID de anulación:\s*([0-9A-Fa-f-]{36})')
    for m in msgs:
        mt = (m.body or '')
        mt = re.sub(r'<[^>]+>',' ', mt)  # strip tags
        g = pat.search(mt)
        if g:
            return g.group(1)
    return None

def _save_pdf_on_move(move, pdf_bytes, filename):
    if not pdf_bytes:
        return
    if 'pdf_fel' in move._fields:
        vals = {'pdf_fel': base64.b64encode(pdf_bytes)}
        if 'pdf_fel_filename' in move._fields:
            vals['pdf_fel_filename'] = filename
        move.write(vals)
    else:
        att = move.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(pdf_bytes),
            'res_model': 'account.move',
            'res_id': move.id,
            'mimetype': 'application/pdf',
        })
        if 'pdf_fel_attachment_id' in move._fields:
            move.write({'pdf_fel_attachment_id': att.id})

# ----------------- modelo -----------------
class AccountMove(models.Model):
    _inherit = "account.move"

    # --------- Botón principal: anular + actualizar PDF + cancelar ---------
    def action_annul_fel_megaprint(self):
        for move in self:
            if not getattr(move, "requiere_certificacion", None):
                raise UserError(_("FEL no instalado correctamente: falta requiere_certificacion()."))
            if not move.requiere_certificacion():
                raise UserError(_("Este documento no requiere certificación FEL."))
            if not getattr(move, "firma_fel", None):
                raise UserError(_("La factura no posee firma FEL; no se puede anular."))

            usuario, apikey, modo = _get_creds(move)
            is_test = _env_is_test(move, modo)
            api_host   = "dev2.api.ifacere-fel.com" if is_test else "apiv2.ifacere-fel.com"
            firma_host = ("dev." if is_test else "") + "api.soluciones-mega.com"

            # 1) token
            token, token_url, raw_token_resp = _request_token(api_host, usuario, apikey)

            # 2) dte de anulación (sin firma)
            if not hasattr(move, "dte_anulacion"):
                raise UserError(_("No se encontró dte_anulacion() en el modelo; verifique fel_gt/fel_megaprint."))
            dte = move.dte_anulacion()
            xml_sin_firma = etree.tostring(dte, encoding="UTF-8").decode("utf-8")

            # 3) firma
            headers_auth = {"Content-Type":"application/xml","authorization":"Bearer "+token,"Accept":"application/xml"}
            req_id = str(uuid.uuid5(uuid.NAMESPACE_OID, str(move.id))).upper()
            sign_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<FirmaDocumentoRequest id="{rid}"><xml_dte><![CDATA[{xml}]]></xml_dte></FirmaDocumentoRequest>'
            ).format(rid=req_id, xml=xml_sin_firma)
            r = requests.post(f'https://{firma_host}/api/solicitaFirma', data=sign_payload.encode('utf-8'), headers=headers_auth, timeout=60)
            try:
                sign_xml = etree.XML((r.text or "").encode('utf-8'))
            except Exception:
                _logger.exception("FirmaResponse inválida: %s", r.text)
                raise UserError(_("Error al firmar XML de anulación.\nRespuesta cruda:\n%s") % (r.text or ""))
            signed_nodes = sign_xml.xpath("//xml_dte")
            if not signed_nodes or not signed_nodes[0].text:
                raise UserError(_("No se obtuvo xml_dte firmado.\nRespuesta:\n%s") % (r.text or ""))
            xml_firmado = html.unescape(signed_nodes[0].text)

            # 4) anulación
            annul_payload = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<AnulaDocumentoXMLRequest id="{rid}"><xml_dte><![CDATA[{xml}]]></xml_dte></AnulaDocumentoXMLRequest>'
            ).format(rid=req_id, xml=xml_firmado)
            r = requests.post(f'https://{api_host}/api/anularDocumentoXML', data=annul_payload.encode('utf-8'), headers=headers_auth, timeout=60)
            try:
                annul_xml = etree.XML((r.text or "").encode('utf-8'))
            except Exception:
                _logger.exception("AnulaResponse inválida: %s", r.text)
                raise UserError(_("Error al enviar anulación.\nRespuesta cruda:\n%s") % (r.text or ""))
            if annul_xml.xpath("//listado_errores"):
                raise UserError(_("Megaprint devolvió errores:\n%s") % (r.text or ""))

            # UUIDs
            original_uuid = getattr(move, 'firma_fel', False)
            annul_uuid_nodes = annul_xml.xpath("//uuid")
            annul_uuid = (annul_uuid_nodes and annul_uuid_nodes[0].text) or False

            # 5) PDF: primero con UUID ORIGINAL (debería venir con sello ANULADO)
            pdf_bytes = None
            try:
                if original_uuid:
                    pdf_bytes = _retornar_pdf_v2(api_host, token, original_uuid)
                if not pdf_bytes and annul_uuid:
                    pdf_bytes = _retornar_pdf_v2(api_host, token, annul_uuid, xml_firmado)  # comprobante de anulación
            except Exception:
                _logger.exception("retornarPDF tras anulación falló")

            _save_pdf_on_move(move, pdf_bytes, f"fel_anulacion_{(original_uuid or annul_uuid or 'doc')}.pdf")

            # 6) Cancelar en Odoo
            cancel_ok = False
            try:
                if hasattr(move, 'button_cancel'):
                    move.button_cancel()
                    cancel_ok = True
            except Exception as e1:
                _logger.info("button_cancel directo falló: %s. Intento por draft…", e1)
            if not cancel_ok:
                try:
                    if hasattr(move, 'button_draft'):
                        move.button_draft()
                    if hasattr(move, 'button_cancel'):
                        move.button_cancel()
                        cancel_ok = True
                except Exception as e2:
                    _logger.exception("No se pudo cancelar la factura tras anular FEL.")
                    raise UserError(_("FEL anulado (UUID: %s), pero no pude cancelar la factura en Odoo.\nDetalle: %s") %
                                    ((annul_uuid or original_uuid or '-'), e2))

            # Mensaje sobrio (sin XMLs crudos)
            body = _("FEL anulado correctamente en Megaprint.")
            if annul_uuid:
                body += _(" UUID de anulación: %s.") % annul_uuid
            move.message_post(body=body)
        return True

    # --------- Botón nuevo: refrescar/actualizar PDF FEL ---------
    def action_refresh_fel_pdf_megaprint(self):
        for move in self:
            if not getattr(move, "requiere_certificacion", None) or not move.requiere_certificacion():
                raise UserError(_("Este documento no requiere certificación FEL."))
            usuario, apikey, modo = _get_creds(move)
            is_test = _env_is_test(move, modo)
            api_host = "dev2.api.ifacere-fel.com" if is_test else "apiv2.ifacere-fel.com"

            token, token_url, raw_token_resp = _request_token(api_host, usuario, apikey)
            original_uuid = getattr(move, 'firma_fel', False)
            pdf_bytes = None

            # 1) intentar con UUID original (payload mínimo)
            if original_uuid:
                pdf_bytes = _retornar_pdf_v2(api_host, token, original_uuid)

            # 2) plan B: UUID de anulación tomado del chatter
            if not pdf_bytes:
                annul_uuid = _extract_annul_uuid_from_chatter(move)
                if annul_uuid:
                    pdf_bytes = _retornar_pdf_v2(api_host, token, annul_uuid)

            if not pdf_bytes:
                raise UserError(_("No fue posible obtener el PDF desde Megaprint. Verifique el UUID y el servicio RetornarPDF."))

            _save_pdf_on_move(move, pdf_bytes, f"fel_actualizado_{(original_uuid or 'doc')}.pdf")
            move.message_post(body=_("PDF FEL actualizado desde Megaprint."))
        return True
