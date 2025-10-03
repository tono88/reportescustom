
# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
import base64
import requests

class FelPreviewStop(Exception):
    """Excepción interna para detener el flujo y mostrar el XML en un wizard."""
    def __init__(self, url, data):
        super().__init__("FEL Preview Stop")
        self.url = url
        self.data = data

def _safe_to_bytes(data):
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode("utf-8", errors="ignore")
    try:
        return bytes(data)
    except Exception:
        return str(data).encode("utf-8", errors="ignore")

class _RequestsCaptureCtx:
    """Context manager para capturar requests.post durante la certificación.
       Soporta 'preview_mode': detiene el primer POST relevante y abre wizard.
    """
    def __init__(self, env, preview_mode=False, preview_confirmed=False):
        self.env = env
        self.preview_mode = preview_mode
        self.preview_confirmed = preview_confirmed
        self.records = []
        self._orig_post = None

    def _match_relevant(self, url):
        # Endpoints habituales en Megaprint/IFACERE
        targets = ("registrarDocumentoXML", "solicitaFirma", "solicitarToken", "retornarPDF")
        return any(t in (url or "") for t in targets)

    def __enter__(self):
        self._orig_post = requests.post

        def _wrapped_post(url, *args, **kwargs):
            # Extraer body que se enviará
            data = None
            if args:
                data = args[0]
            if "data" in kwargs:
                data = kwargs["data"]

            # Si estamos en preview y aún no está confirmado, detener en el primer POST relevante
            if self.preview_mode and not self.preview_confirmed and self._match_relevant(url):
                # Guardamos para el wizard y detenemos el flujo
                raise FelPreviewStop(url, data)

            # Camino normal: enviar y registrar
            resp = self._orig_post(url, *args, **kwargs)
            try:
                self.records.append({
                    "url": url,
                    "data": data,
                    "status_code": getattr(resp, "status_code", None),
                    "text": getattr(resp, "text", ""),
                })
            except Exception:
                pass
            return resp

        requests.post = _wrapped_post
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._orig_post:
            requests.post = self._orig_post

class AccountMove(models.Model):
    _inherit = "account.move"

    # ---------- Utilidades ----------
    def _fel_attach_xml(self, name, xml_text):
        self.ensure_one()
        if not xml_text:
            return
        self.env["ir.attachment"].create({
            "name": name,
            "res_model": self._name,
            "res_id": self.id,
            "type": "binary",
            "mimetype": "application/xml",
            "datas": base64.b64encode(_safe_to_bytes(xml_text)),
        })

    @api.model
    def _fel_filename_for_url(self, url, is_response=False):
        suffix = "RESP" if is_response else "REQ"
        if "solicitarToken" in (url or ""):
            return f"FEL-TOKEN-{suffix}.xml"
        if "solicitaFirma" in (url or ""):
            return f"FEL-FIRMA-{suffix}.xml"
        if "registrarDocumentoXML" in (url or ""):
            return f"FEL-REGISTRO-{suffix}.xml"
        if "retornarPDF" in (url or ""):
            return f"FEL-RETORNARPDF-{suffix}.xml"
        return f"FEL-OTRO-{suffix}.xml"

    def _certify_call_super(self):
        """Llamar al método original del módulo fel_megaprint."""
        return super(AccountMove, self).certificar_megaprint()

    def _fel_certify_with_capture(self, preview_mode=False, preview_confirmed=False):
        """Ejecuta la certificación capturando XML; en preview, abre wizard antes de enviar."""
        self.ensure_one()
        action = None
        with _RequestsCaptureCtx(self.env, preview_mode=preview_mode, preview_confirmed=preview_confirmed) as cap:
            try:
                res = self._certify_call_super()
            except FelPreviewStop as st:
                # Abrir wizard con el XML que iba a enviarse
                wiz = self.env["fel.megaprint.preview.wizard"].create({
                    "move_id": self.id,
                    "endpoint": st.url or "",
                    "xml_text": (_safe_to_bytes(st.data).decode("utf-8", errors="ignore") if st.data else ""),
                })
                action = wiz.action_open()
                return action  # detenemos aquí; no se envió nada aún

        # Si llegamos aquí (sin excepción), adjuntar lo capturado (requests/responses)
        for rec in cap.records:
            req_fname = self._fel_filename_for_url(rec.get("url"), is_response=False)
            self._fel_attach_xml(req_fname, rec.get("data"))
            resp_fname = self._fel_filename_for_url(rec.get("url"), is_response=True)
            self._fel_attach_xml(resp_fname, rec.get("text"))

        return res

    # ---------- Entradas desde la UI ----------
    def action_fel_preview_certify(self):
        """Botón: Previsualizar XML antes de certificar."""
        self.ensure_one()
        return self._fel_certify_with_capture(preview_mode=True, preview_confirmed=False)

    # Mantener el comportamiento normal (certificar directo), con captura adjunta
    def certificar_megaprint(self):
        self.ensure_one()
        # Camino estándar sin preview: adjunta los XML de request/response
        return self._fel_certify_with_capture(preview_mode=False, preview_confirmed=False)
