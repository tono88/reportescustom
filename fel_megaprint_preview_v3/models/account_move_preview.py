
# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import UserError
import requests
import json as pyjson

DESIRED_ENDPOINTS = ("registrarDocumentoXML", "solicitaFirma")

def _to_text(data):
    if data is None:
        return ""
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return repr(data)
    if isinstance(data, (dict, list)):
        # pretty json for readability (some modules send JSON with 'xml' field)
        try:
            return pyjson.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            return str(data)
    return str(data)

def _extract_xml_from_request(body, json_data, files):
    # 1) Common JSON fields carrying XML
    if isinstance(json_data, dict):
        for k in ("xml", "dte", "xmldte", "xml_dte", "documento", "gtDocumento", "GTDocumento"):
            if k in json_data and isinstance(json_data[k], (str, bytes)):
                return _to_text(json_data[k])
    # 2) 'data' as dict (form-encoded) with xml
    if isinstance(body, dict):
        for k in ("xml", "dte", "xmldte", "xml_dte", "documento", "gtDocumento", "GTDocumento"):
            if k in body and isinstance(body[k], (str, bytes)):
                return _to_text(body[k])
    # 3) Files upload: ('file', ('name.xml', b'...xml...', 'application/xml'))
    if files:
        if isinstance(files, dict):
            candidates = files.values()
        elif isinstance(files, (list, tuple)):
            candidates = [x[1] if isinstance(x, (list, tuple)) and len(x) >= 2 else x for x in files]
        else:
            candidates = []
        for cand in candidates:
            # cand can be tuple ('name', bytes [, mime])
            if isinstance(cand, (list, tuple)) and len(cand) >= 2:
                content = cand[1]
                if isinstance(content, (bytes, str)):
                    txt = _to_text(content)
                    if "<" in txt and ">" in txt:
                        return txt
    # 4) Raw body as xml string
    txt = _to_text(body)
    if "<" in txt and ">" in txt and "<dte:" in txt or "<GTDocumento" in txt or "<Documento" in txt:
        return txt
    return ""

class FelPreviewStop(Exception):
    def __init__(self, url, xml_text):
        super().__init__("FEL Preview Stop")
        self.url = url
        self.xml_text = xml_text or ""

class _MockResponse:
    def __init__(self, text='{"ok": true, "token": "DUMMY"}', status_code=200):
        self.text = text
        self.status_code = status_code
        self.content = text.encode("utf-8", errors="ignore")
    def json(self):
        try:
            return pyjson.loads(self.text)
        except Exception:
            return {"ok": True}

class _InterceptUntilTargetPost:
    """Interceta requests.post y permite que el flujo avance con respuestas simuladas,
       hasta que se intente POST a un endpoint que sí lleva el DTE (registrarDocumentoXML o solicitaFirma).
       En ese punto, se captura el XML y se lanza la excepción para abrir el wizard.
    """
    def __init__(self):
        self._orig_post = None

    def __enter__(self):
        self._orig_post = requests.post

        def _wrapped_post(url, *args, **kwargs):
            url = url or ""
            body = None
            json_data = kwargs.get("json")
            data_kw = kwargs.get("data")
            files = kwargs.get("files")

            # Body por prioridad: args[0] -> kwargs['data'] -> kwargs['json']
            if args:
                body = args[0]
            elif data_kw is not None:
                body = data_kw
            elif json_data is not None:
                body = json_data

            # Si es un endpoint con el DTE, extraemos el XML y detenemos
            if any(ep in url for ep in DESIRED_ENDPOINTS):
                xml_text = _extract_xml_from_request(body, json_data, files)
                raise FelPreviewStop(url, xml_text)

            # Para endpoints NO deseados, devolvemos respuesta simulada para que el flujo avance sin salir a internet
            # generar token/respuesta OK dummy
            dummy_text = '{"ok": true, "token": "DUMMY"}' if "solicitarToken" in url else '{"ok": true}'
            return _MockResponse(text=dummy_text, status_code=200)

        requests.post = _wrapped_post
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._orig_post:
            requests.post = self._orig_post

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_fel_preview_xml(self):
        """Ejecuta el flujo de certificación SIN salir a red y muestra el XML del DTE (factura) en wizard."""
        self.ensure_one()
        original = getattr(super(AccountMove, self), "certificar_megaprint", None)
        if not original:
            raise UserError(_("No se encontró 'certificar_megaprint' del módulo FEL Megaprint."))

        try:
            with _InterceptUntilTargetPost():
                original()  # Nunca llegará a internet: devolveremos mocks hasta capturar el DTE
        except FelPreviewStop as st:
            xml_text = st.xml_text.strip() or _("No se pudo detectar el XML DTE en la solicitud.")
            wiz = self.env["fel.megaprint.preview.wizard"].create({
                "move_id": self.id,
                "endpoint": st.url or "",
                "xml_text": xml_text,
            })
            return wiz.action_open()

        raise UserError(_("No se detectó ninguna llamada con el DTE (registrarDocumentoXML/solicitaFirma)."))
