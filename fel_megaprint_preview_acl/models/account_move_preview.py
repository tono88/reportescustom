
# -*- coding: utf-8 -*-
from odoo import models, api, fields, _
from odoo.exceptions import UserError
import requests

class FelPreviewStop(Exception):
    """Excepción para detener el flujo en el primer POST relevante y mostrar el XML."""
    def __init__(self, url, data):
        super().__init__("FEL Preview Stop")
        self.url = url
        self.data = data

def _to_text(data):
    if data is None:
        return ""
    if isinstance(data, bytes):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return repr(data)
    return str(data)

class _InterceptFirstPost:
    """Intercepta requests.post y detiene el flujo en el primer endpoint FEL relevante."""
    def __init__(self):
        self._orig_post = None

    def _is_target(self, url: str):
        url = url or ""
        return any(x in url for x in (
            "registrarDocumentoXML",
            "solicitaFirma",
            "solicitarToken",
            "retornarPDF",
        ))

    def __enter__(self):
        self._orig_post = requests.post

        def _wrapped_post(url, *args, **kwargs):
            body = None
            if args:
                body = args[0]
            if "data" in kwargs:
                body = kwargs["data"]
            # Detener SIEMPRE antes de enviar a red
            raise FelPreviewStop(url, body)

        requests.post = _wrapped_post
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._orig_post:
            requests.post = self._orig_post

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_fel_preview_xml(self):
        """Genera el XML de certificación y lo muestra en un wizard SIN ENVIAR NADA."""
        self.ensure_one()
        original = getattr(super(AccountMove, self), "certificar_megaprint", None)
        if not original:
            raise UserError(_("No se encontró 'certificar_megaprint' del módulo FEL Megaprint."))

        with _InterceptFirstPost():
            try:
                original()  # se detendrá antes del primer POST
            except FelPreviewStop as st:
                xml_text = _to_text(st.data).strip() or _("No se detectó un cuerpo XML listo para enviar.")
                wiz = self.env["fel.megaprint.preview.wizard"].create({
                    "move_id": self.id,
                    "endpoint": st.url or "",
                    "xml_text": xml_text,
                })
                return wiz.action_open()

        raise UserError(_("No se detectó ninguna llamada a Megaprint/IFACERE durante la previsualización."))
