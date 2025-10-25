# -*- coding: utf-8 -*-
import logging, re, threading, uuid, time
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
from requests.exceptions import Timeout, ConnectionError

_logger = logging.getLogger(__name__)
_tl = threading.local()

UUID_RE = re.compile(r"[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}", re.I)

class AccountMove(models.Model):
    _inherit = "account.move"

    fel_request_id = fields.Char("FEL Request ID", copy=False)

    def _get_retry_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        attempts = int(ICP.get_param('megaprint.retry_attempts', '3'))
        base = float(ICP.get_param('megaprint.retry_backoff_base', '0.6'))
        timeout = float(ICP.get_param('megaprint.request_timeout_seconds', '60'))
        use_uuid_endpoint = ICP.get_param('megaprint.use_uuid_endpoint', '1') == '1'
        return attempts, base, timeout, use_uuid_endpoint

    def certificar_megaprint(self):
        """Enforce unique request id and (optionally) switch to registrarDocumentoUuid.
        Delegates actual send to original implementation.
        """
        attempts, base, default_timeout, use_uuid_endpoint = self._get_retry_params()

        original_post = requests.post

        def _inject_id_and_switch(url, *args, **kwargs):
            # Ensure timeout
            if 'timeout' not in kwargs or not kwargs['timeout']:
                kwargs['timeout'] = default_timeout

            # Switch endpoint if configured
            if use_uuid_endpoint and isinstance(url, str) and '/registrarDocumentoXML' in url:
                url = url.replace('/registrarDocumentoXML', '/registrarDocumentoUuid')

            # Inject id attribute in request XML body if present
            rid = getattr(_tl, 'rid', None)
            data = kwargs.get('data')
            if isinstance(data, (bytes, bytearray)):
                try:
                    data_str = data.decode('utf-8', errors='ignore')
                except Exception:
                    data_str = None
            else:
                data_str = data if isinstance(data, str) else None

            if rid and data_str and ('<xml' in data_str or '<Registra' in data_str):
                # set id="RID" in the first opening tag that looks like *Request ...>
                def repl_id(m):
                    tag = m.group(0)
                    if ' id=' in tag or ' ID=' in tag:
                        tag = re.sub(r'\s(id|ID)=\"[^\"]*\"', ' id="%s"' % rid, tag)
                    else:
                        tag = tag[:-1] + ' id="%s">' % rid
                    return tag
                data_str = re.sub(r'<([A-Za-z]+\w*Request)([^>]*)>', repl_id, data_str, count=1)
                kwargs['data'] = data_str

            # Basic retries for transient errors
            last_exc = None
            RETRYABLE_STATUS = {502, 503, 504}
            for attempt in range(1, attempts + 1):
                try:
                    resp = original_post(url, *args, **kwargs)
                    if resp.status_code in RETRYABLE_STATUS:
                        _logger.warning("[MEGAPRINT][retryable %s] intento=%s/%s url=%s", resp.status_code, attempt, attempts, url)
                        if attempt < attempts:
                            time.sleep(base * (2 ** (attempt - 1)))
                            continue
                    return resp
                except (Timeout, ConnectionError) as exc:
                    last_exc = exc
                    _logger.warning("[MEGAPRINT][timeout/conn] intento=%s/%s url=%s err=%s", attempt, attempts, url, exc)
                    if attempt < attempts:
                        time.sleep(base * (2 ** (attempt - 1)))
                        continue
                    raise
            if last_exc:
                raise last_exc

        results = self.env['account.move']
        for move in self:
            if not move.fel_request_id:
                move.write({'fel_request_id': str(uuid.uuid4()).upper()})
            _tl.rid = move.fel_request_id
            requests.post = _inject_id_and_switch
            try:
                res = super(AccountMove, move).certificar_megaprint()
                results |= move
            finally:
                requests.post = original_post
                _tl.rid = None
        return results
