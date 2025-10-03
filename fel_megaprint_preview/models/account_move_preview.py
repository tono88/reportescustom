
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
        self.captured_url = None
        self.captured_data = None

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
            if self._is_target(url):
                # Guardar y detener ANTES de enviar
                self.captured_url = url
                self.captured_data = body
                raise FelPreviewStop(url, body)
            # Cualquier otro POST (no FEL), NO lo enviamos tampoco para seguridad
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
        # Validar que exista el método original
        original = getattr(super(AccountMove, self), "certificar_megaprint", None)
        if not original:
            raise UserError(_("No se encontró 'certificar_megaprint' del módulo FEL Megaprint."))

        # Interceptar cualquier post de red y detener el flujo antes de salir
        with _InterceptFirstPost() as cap:
            try:
                # Ejecutamos el flujo original. Se frenará antes del primer POST.
                original()
            except FelPreviewStop as st:
                xml_text = _to_text(st.data).strip()
                if not xml_text:
                    xml_text = _("No se detectó un cuerpo XML listo para enviar.")
                wiz = self.env["fel.megaprint.preview.wizard"].create({
                    "move_id": self.id,
                    "endpoint": st.url or "",
                    "xml_text": xml_text,
                })
                return wiz.action_open()

        # Si por alguna razón no hubo POST ni excepción (muy raro), informar:
        raise UserError(_("No se detectó ninguna llamada a Megaprint/IFACERE durante la previsualización."))
