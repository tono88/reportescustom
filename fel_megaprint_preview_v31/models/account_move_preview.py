
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
        try:
            return pyjson.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            return str(data)
    return str(data)

def _extract_xml_from_request(body, json_data, files):
    # 1) JSON payloads
    if isinstance(json_data, dict):
        for k in ("xml", "dte", "xmldte", "xml_dte", "documento", "gtDocumento", "GTDocumento"):
            if k in json_data and isinstance(json_data[k], (str, bytes)):
                return _to_text(json_data[k])
    # 2) Form data dict
    if isinstance(body, dict):
        for k in ("xml", "dte", "xmldte", "xml_dte", "documento", "gtDocumento", "GTDocumento"):
            if k in body and isinstance(body[k], (str, bytes)):
                return _to_text(body[k])
    # 3) Files
    if files:
        if isinstance(files, dict):
            candidates = files.values()
        elif isinstance(files, (list, tuple)):
            candidates = [x[1] if isinstance(x, (list, tuple)) and len(x) >= 2 else x for x in files]
        else:
            candidates = []
        for cand in candidates:
            if isinstance(cand, (list, tuple)) and len(cand) >= 2:
                content = cand[1]
                if isinstance(content, (bytes, str)):
                    txt = _to_text(content)
                    if "<" in txt and ">" in txt:
                        return txt
    # 4) Raw body
    txt = _to_text(body)
    if ("<" in txt and ">" in txt) and ("<dte:" in txt or "<GTDocumento" in txt or "<Documento" in txt or "<SAT" in txt):
        return txt
    return ""

class FelPreviewStop(Exception):
    def __init__(self, url, xml_text):
        super().__init__("FEL Preview Stop")
        self.url = url
        self.xml_text = xml_text or ""

class _MockResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.content = text.encode("utf-8", errors="ignore")
    def json(self):
        try:
            return pyjson.loads(self.text)
        except Exception:
            return {"ok": True}

def _xml_ok(tag="Respuesta", **fields):
    # Construye un XML minimal válido con campos simples
    parts = [f"<{tag}>"]
    for k, v in fields.items():
        parts.append(f"<{k}>{v}</{k}>")
    parts.append(f"</{tag}>")
    return "".join(parts)

class _InterceptUntilTargetPost:
    """Mockea respuestas XML en endpoints no objetivo y detiene en registrarDocumentoXML/solicitaFirma."""
    def __init__(self):
        self._orig_post = None

    def __enter__(self):
        self._orig_post = requests.post

        def _wrapped_post(url, *args, **kwargs):
            url = url or ""
            json_data = kwargs.get("json")
            data_kw = kwargs.get("data")
            files = kwargs.get("files")
            body = args[0] if args else (data_kw if data_kw is not None else json_data)

            # Objetivo: capturar DTE
            if any(ep in url for ep in DESIRED_ENDPOINTS):
                xml_text = _extract_xml_from_request(body, json_data, files)
                raise FelPreviewStop(url, xml_text)

            # Mocks XML para que el código que hace etree.XML(r.text) no falle
            if "solicitarToken" in url:
                # Ejemplo de respuesta XML con token
                return _MockResponse(_xml_ok("RespuestaToken", ok="true", token="DUMMY"))
            if "retornarPDF" in url:
                return _MockResponse(_xml_ok("RespuestaPDF", ok="true"))
            # Genérico XML OK
            return _MockResponse(_xml_ok("Respuesta", ok="true"))

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
                original()
        except FelPreviewStop as st:
            xml_text = (st.xml_text or "").strip() or _("No se pudo detectar el XML DTE en la solicitud.")
            wiz = self.env["fel.megaprint.preview.wizard"].create({
                "move_id": self.id,
                "endpoint": st.url or "",
                "xml_text": xml_text,
            })
            return wiz.action_open()

        raise UserError(_("No se detectó ninguna llamada con el DTE (registrarDocumentoXML/solicitaFirma)."))
