# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import uuid
import logging
import time
import requests
from requests.exceptions import Timeout, ConnectionError

_logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {502, 503, 504}

class AccountMove(models.Model):
    _inherit = "account.move"

    fel_cert_in_progress = fields.Boolean(string='FEL: certificación en curso', copy=False, default=False)
    fel_request_id = fields.Char(string='FEL Request ID', copy=False)

    def _lock_for_cert(self):
        # Lock the row NOWAIT to avoid concurrent certification of the same invoice
        self.env.cr.execute("SELECT id FROM account_move WHERE id IN %s FOR UPDATE NOWAIT", [tuple(self.ids)])
        return True

    def _get_retry_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        # Defaults sensatos
        attempts = int(ICP.get_param('megaprint.retry_attempts', '3'))
        base = float(ICP.get_param('megaprint.retry_backoff_base', '0.6'))  # segundos
        timeout = float(ICP.get_param('megaprint.request_timeout_seconds', '60'))
        return attempts, base, timeout

    def certificar_megaprint(self):
        """Wrapper que agrega candado transaccional, idempotencia, timeout y reintentos con backoff.
        Luego delega en la implementación original del módulo fel_megaprint.
        """
        attempts, base, default_timeout = self._get_retry_params()

        # Preparar candado y request_id por cada factura
        for move in self:
            if not getattr(move.journal_id, 'usuario_fel', False):
                continue

            if getattr(move, 'firma_fel', False):
                raise UserError(_("La factura ya fue validada, por lo que no puede ser validada nuevamente"))

            try:
                move._lock_for_cert()
            except Exception:
                raise UserError(_("Esta factura ya está siendo certificada. Intenta nuevamente en unos segundos."))

            if move.fel_cert_in_progress:
                raise UserError(_("Certificación FEL ya en curso para esta factura."))

            rid = move.fel_request_id or str(uuid.uuid5(uuid.NAMESPACE_OID, str(move.id))).upper()
            move.write({'fel_cert_in_progress': True, 'fel_request_id': rid})
            _logger.info("[MEGAPRINT] Inicio certificación move_id=%s rid=%s", move.id, rid)

        # Monkeypatch de requests.post para inyectar timeout y reintentos alrededor del post original
        original_post = requests.post

        def _post_with_timeout_and_retry(url, *args, **kwargs):
            # asegurar timeout por defecto
            if 'timeout' not in kwargs or not kwargs['timeout']:
                kwargs['timeout'] = default_timeout

            # logging mínimo (evitar volcar XML completo)
            body = kwargs.get('data') or kwargs.get('json')
            body_info = ""
            if body is not None:
                try:
                    body_info = f" (len={len(body)})" if hasattr(body, '__len__') else " (body)"
                except Exception:
                    body_info = " (body)"
            # intentos
            last_exc = None
            for attempt in range(1, attempts + 1):
                try:
                    resp = original_post(url, *args, **kwargs)
                    if resp.status_code in RETRYABLE_STATUS:
                        _logger.warning("[MEGAPRINT][retryable %s] url=%s%s intento=%s/%s",
                                        resp.status_code, url, body_info, attempt, attempts)
                        # backoff exponencial simple
                        if attempt < attempts:
                            time.sleep(base * (2 ** (attempt - 1)))
                            continue
                    return resp
                except (Timeout, ConnectionError) as exc:
                    last_exc = exc
                    _logger.warning("[MEGAPRINT][timeout/conn] url=%s%s intento=%s/%s error=%s",
                                    url, body_info, attempt, attempts, str(exc))
                    if attempt < attempts:
                        time.sleep(base * (2 ** (attempt - 1)))
                        continue
                    raise
            # si sale del loop, re-raise última excepción por seguridad
            if last_exc:
                raise last_exc

        # parchear
        requests.post = _post_with_timeout_and_retry
        try:
            res = super(AccountMove, self).certificar_megaprint()
            return res
        finally:
            # restaurar
            requests.post = original_post
            # limpiar flags y loguear fin
            for move in self:
                if move.fel_cert_in_progress:
                    move.write({'fel_cert_in_progress': False})
                    _logger.info("[MEGAPRINT] Fin certificación move_id=%s rid=%s", move.id, move.fel_request_id or '')