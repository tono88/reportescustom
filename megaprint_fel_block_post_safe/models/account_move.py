# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging, time, base64

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = "account.move"

    def _bb_cfg(self):
        ICP = self.env['ir.config_parameter'].sudo()
        def _get(name, default):
            try:
                return ICP.get_param(name, default)
            except Exception:
                return default
        return {
            'block_enabled': _get('megaprint.block_post_until_fel', '1') == '1',
            'wait_timeout': int(_get('megaprint.wait_timeout_seconds', '60')),
            'call_if_missing': _get('megaprint.call_cert_if_missing', '1') == '1',
            'poll_seconds': int(_get('megaprint.poll_seconds', '2')),
            'require_full_fel': _get('megaprint.require_full_fel', '0') == '1',
            'chatter_audit': _get('megaprint.chatter_audit', '1') == '1',
            'attach_files': _get('megaprint.attach_files_in_chatter', '1') == '1',
            'attach_xml_result': _get('megaprint.attach_xml_result', '1') == '1',
        }

    def _bb_needs_fel(self):
        self.ensure_one()
        if getattr(self, 'move_type', '') != 'out_invoice':
            return False
        journal = self.journal_id
        generar = getattr(journal, 'generar_fel', False)
        if not generar:
            return False
        return hasattr(self, 'certificar_megaprint')

    def _bb_has_fel_fields(self):
        self.ensure_one()
        firma = getattr(self, 'firma_fel', False)
        serie = getattr(self, 'serie_fel', False)
        numero = getattr(self, 'numero_fel', False)
        cfg = self._bb_cfg()
        if cfg['require_full_fel']:
            return bool(firma and serie and numero)
        return bool(firma)

    def _bb_refresh_fields(self, rec, fields):
        try:
            rec.invalidate_recordset(fields)
            return
        except Exception:
            pass
        try:
            rec.invalidate_cache(fields)
            return
        except Exception:
            pass
        rec.read(fields)

    # ---------- Attachments helpers ----------
    def _bb_guess_binary_fields(self, move):
        """Return dict of possible binary fields for xml/pdf in the move."""
        fields = move._fields
        names = list(fields.keys())
        xml_candidates = [n for n in names if 'fel' in n and 'xml' in n and fields[n].type == 'binary']
        pdf_candidates = [n for n in names if 'fel' in n and 'pdf' in n and fields[n].type == 'binary']
        # Common fallbacks
        xml_candidates += [n for n in ['documento_xml_fel','xml_fel','fel_xml','fel_xml_document','xml_documento_fel'] if n in names]
        pdf_candidates += [n for n in ['pdf_fel','fel_pdf','fel_pdf_document','documento_pdf_fel'] if n in names]
        # De-duplicate while preserving order
        seen = set(); xml_candidates = [x for x in xml_candidates if not (x in seen or seen.add(x))]
        seen = set(); pdf_candidates = [x for x in pdf_candidates if not (x in seen or seen.add(x))]
        return {'xml': xml_candidates, 'pdf': pdf_candidates}

    def _bb_collect_fel_attachments(self, move):
        cfg = self._bb_cfg()
        att = []
        cand = self._bb_guess_binary_fields(move)
        def _add(field_name, filename, mimetype):
            try:
                data = getattr(move, field_name, False)
            except Exception:
                data = False
            if data:
                # data is expected base64-encoded string in Odoo
                att.append((filename, data, mimetype))
        # Document XML
        for fname in cand['xml']:
            _add(fname, (move.name or 'invoice') + '_fel.xml', 'application/xml')
            break
        # PDF
        for fname in cand['pdf']:
            _add(fname, (move.name or 'invoice') + '_fel.pdf', 'application/pdf')
            break
        # Optionally try result xml (second XML)
        if cfg['attach_xml_result']:
            res_fields = [n for n in move._fields.keys() if 'resultado' in n and 'xml' in n and move._fields[n].type == 'binary']
            for rf in res_fields:
                _add(rf, (move.name or 'invoice') + '_fel_result.xml', 'application/xml')
                break
        return att

    def _bb_already_posted_success(self, move):
        # avoid duplicate chatter success by scanning last few messages
        try:
            msgs = self.env['mail.message'].sudo().search_read(
                [('model','=','account.move'),('res_id','=',move.id)], ['body'], limit=5, order='id desc')
            for m in msgs:
                if 'FEL certificado' in (m.get('body') or ''):
                    return True
        except Exception:
            pass
        return False

    def _bb_chatter_success(self, move):
        cfg = self._bb_cfg()
        if not cfg['chatter_audit'] or self._bb_already_posted_success(move):
            return
        firma = getattr(move, 'firma_fel', '') or ''
        serie = getattr(move, 'serie_fel', '') or ''
        numero = getattr(move, 'numero_fel', '') or ''
        rid = getattr(move, 'fel_request_id', '') or ''
        parts = ["<b>FEL certificado</b>"]
        if firma:
            parts.append("UUID: <code>%s</code>" % firma)
        if serie:
            parts.append("Serie: <code>%s</code>" % serie)
        if numero:
            parts.append("Número: <code>%s</code>" % numero)
        if rid:
            parts.append("Request ID: <code>%s</code>" % rid)
        body = " — ".join(parts)
        attach_ids = []
        if cfg['attach_files']:
            try:
                to_attach = self._bb_collect_fel_attachments(move)
                for (filename, b64, mimetype) in to_attach:
                    att = self.env['ir.attachment'].sudo().create({
                        'name': filename,
                        'datas': b64,
                        'res_model': 'account.move',
                        'res_id': move.id,
                        'mimetype': mimetype,
                    })
                    attach_ids.append(att.id)
            except Exception as e:
                _logger.warning("[FEL_BLOCK_SAFE] Could not build attachments: %s", e)
        try:
            if attach_ids:
                move.message_post(body=body, message_type='comment', attachment_ids=[(4, i) for i in attach_ids])
            else:
                move.message_post(body=body, message_type='comment')
        except Exception as e:
            _logger.warning("[FEL_BLOCK_SAFE] Could not post success message: %s", e)

    def _bb_chatter_timeout(self, move, seconds):
        cfg = self._bb_cfg()
        if not cfg['chatter_audit']:
            return
        rid = getattr(move, 'fel_request_id', '') or ''
        body = ("<b>FEL no recibido</b> en %ss — se abortó el posteo para evitar inconsistencias." % seconds) +                (" Request ID: <code>%s</code>" % rid if rid else "")
        try:
            move.message_post(body=body, message_type='comment')
        except Exception as e:
            _logger.warning("[FEL_BLOCK_SAFE] Could not post timeout message: %s", e)

    # ---------- Wait logic ----------
    def _bb_wait_fel_or_fail(self):
        cfg = self._bb_cfg()
        if not cfg['block_enabled']:
            return
        for move in self:
            if not move._bb_needs_fel():
                continue
            if move._bb_has_fel_fields():
                self._bb_chatter_success(move)
                continue
            if cfg['call_if_missing'] and hasattr(move, 'certificar_megaprint'):
                try:
                    _logger.info("[FEL_BLOCK_SAFE] Trigger certificar_megaprint (missing FEL) move_id=%s", move.id)
                    move.certificar_megaprint()
                except Exception as e:
                    _logger.warning("[FEL_BLOCK_SAFE] certificar_megaprint() raised: %s", e)
            start = time.time()
            while time.time() - start < cfg['wait_timeout']:
                self._bb_refresh_fields(move, ['firma_fel','serie_fel','numero_fel'])
                if move._bb_has_fel_fields():
                    _logger.info("[FEL_BLOCK_SAFE] FEL present after wait move_id=%s", move.id)
                    self._bb_chatter_success(move)
                    break
                time.sleep(max(1, cfg['poll_seconds']))
            else:
                self._bb_chatter_timeout(move, cfg['wait_timeout'])
                raise UserError(_("FEL certification not received within %s seconds; posting aborted.") % cfg['wait_timeout'])

    def action_post(self):
        res = super().action_post()
        self._bb_wait_fel_or_fail()
        return res

    def write(self, vals):
        posting = 'state' in vals and vals.get('state') == 'posted'
        res = super().write(vals)
        if posting:
            self._bb_wait_fel_or_fail()
        return res
