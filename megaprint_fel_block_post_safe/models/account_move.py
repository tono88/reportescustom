# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError
import logging, time, html
import requests

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
            "block_enabled": _get("megaprint.block_post_until_fel", "1") == "1",
            "wait_timeout": int(_get("megaprint.wait_timeout_seconds", "60")),
            "call_if_missing": _get("megaprint.call_cert_if_missing", "1") == "1",
            "poll_seconds": int(_get("megaprint.poll_seconds", "2")),
            "require_full_fel": _get("megaprint.require_full_fel", "1") == "1",
            "chatter_audit": _get("megaprint.chatter_audit", "1") == "1",
            "attach_files": _get("megaprint.attach_files_in_chatter", "1") == "1",
            "attach_xml_result": _get("megaprint.attach_xml_result", "1") == "1",
            "log_http": _get("megaprint.log_http_response", "1") == "1",
            "http_log_max": int(_get("megaprint.http_log_max_chars", "2000")),
            "include_http_in_popup": _get("megaprint.include_http_in_popup", "1") == "1",
            "popup_http_max": int(_get("megaprint.popup_http_max_chars", "600")),
        }

    def _bb_needs_fel(self):
        self.ensure_one()
        if getattr(self, "move_type", "") != "out_invoice":
            return False
        journal = self.journal_id
        generar = getattr(journal, "generar_fel", False)
        if not generar:
            return False
        return hasattr(self, "certificar_megaprint")

    def _bb_has_fel_fields(self):
        self.ensure_one()
        firma = getattr(self, "firma_fel", False)
        serie = getattr(self, "serie_fel", False)
        numero = getattr(self, "numero_fel", False)
        cfg = self._bb_cfg()
        if cfg["require_full_fel"]:
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

    # ---------- HTTP capture ----------
    def _bb_capture_http(self):
        cfg = self._bb_cfg()
        captured = {"url": None, "status": None, "text": None}
        if not cfg["log_http"]:
            class Dummy:
                def __enter__(self2): return None
                def __exit__(self2, *exc): return False
            return captured, Dummy()
        original_post = requests.post
        def wrapped(url, *args, **kwargs):
            resp = original_post(url, *args, **kwargs)
            try:
                captured["url"] = str(url)
                captured["status"] = getattr(resp, "status_code", None)
                captured["text"] = getattr(resp, "text", "") or ""
            except Exception:
                pass
            return resp
        class PatchCtx:
            def __enter__(self2):
                requests.post = wrapped
            def __exit__(self2, exc_type, exc, tb):
                requests.post = original_post
                return False
        return captured, PatchCtx()

    def _bb_render_http_snippet_html(self, captured):
        if not captured or not captured.get("url"):
            return ""
        cfg = self._bb_cfg()
        maxc = max(100, min(10000, cfg["http_log_max"]))
        text = captured.get("text") or ""
        if len(text) > maxc:
            text = text[:maxc] + "\n...[truncated]"
        esc = html.escape(text)
        url = html.escape(captured.get("url") or "")
        status = captured.get("status")
        head = "URL: <code>%s</code> - Status: <code>%s</code>" % (url, status)
        body = "<pre style='white-space:pre-wrap;max-height:360px;overflow:auto'>%s</pre>" % esc
        return head + "<br/>" + body

    def _bb_render_http_snippet_text(self, captured):
        if not captured or not captured.get("url"):
            return "(no HTTP response captured)"
        cfg = self._bb_cfg()
        maxc = max(80, min(5000, cfg["popup_http_max"]))
        text = captured.get("text") or ""
        if len(text) > maxc:
            text = text[:maxc] + "\n...[truncated]"
        url = captured.get("url") or ""
        status = captured.get("status")
        return "URL: %s\nStatus: %s\nBody:\n%s" % (url, status, text)

    # ---------- Chatter helpers ----------
    def _bb_guess_binary_fields(self, move):
        fields = move._fields
        names = list(fields.keys())
        xml_candidates = [n for n in names if "fel" in n and "xml" in n and fields[n].type == "binary"]
        pdf_candidates = [n for n in names if "fel" in n and "pdf" in n and fields[n].type == "binary"]
        xml_candidates += [n for n in ["documento_xml_fel","xml_fel","fel_xml","fel_xml_document","xml_documento_fel"] if n in names]
        pdf_candidates += [n for n in ["pdf_fel","fel_pdf","fel_pdf_document","documento_pdf_fel"] if n in names]
        seen = set(); xml_candidates = [x for x in xml_candidates if not (x in seen or seen.add(x))]
        seen = set(); pdf_candidates = [x for x in pdf_candidates if not (x in seen or seen.add(x))]
        return {"xml": xml_candidates, "pdf": pdf_candidates}

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
                att.append((filename, data, mimetype))
        for fname in cand["xml"]:
            _add(fname, (move.name or "invoice") + "_fel.xml", "application/xml")
            break
        for fname in cand["pdf"]:
            _add(fname, (move.name or "invoice") + "_fel.pdf", "application/pdf")
            break
        if cfg["attach_xml_result"]:
            res_fields = [n for n in move._fields.keys() if "resultado" in n and "xml" in n and move._fields[n].type == "binary"]
            for rf in res_fields:
                _add(rf, (move.name or "invoice") + "_fel_result.xml", "application/xml")
                break
        return att

    def _bb_already_posted_success(self, move):
        try:
            msgs = self.env["mail.message"].sudo().search_read(
                [("model","=","account.move"),("res_id","=",move.id)], ["body"], limit=5, order="id desc")
            for m in msgs:
                if "FEL certificado" in (m.get("body") or ""):
                    return True
        except Exception:
            pass
        return False

    def _bb_chatter_success(self, move, extra_html=""):
        cfg = self._bb_cfg()
        if not cfg["chatter_audit"] or self._bb_already_posted_success(move):
            return
        firma = getattr(move, "firma_fel", "") or ""
        serie = getattr(move, "serie_fel", "") or ""
        numero = getattr(move, "numero_fel", "") or ""
        rid = getattr(move, "fel_request_id", "") or ""
        parts = ["<b>FEL certificado</b>"]
        if firma:
            parts.append("UUID: <code>%s</code>" % firma)
        if serie:
            parts.append("Serie: <code>%s</code>" % serie)
        if numero:
            parts.append("Numero: <code>%s</code>" % numero)
        if rid:
            parts.append("Request ID: <code>%s</code>" % rid)
        body = " — ".join(parts)
        if extra_html:
            body += "<br/><br/><b>Ultima respuesta FEL:</b><br/>" + extra_html
        attach_ids = []
        if cfg["attach_files"]:
            try:
                to_attach = self._bb_collect_fel_attachments(move)
                for (filename, b64, mimetype) in to_attach:
                    att = self.env["ir.attachment"].sudo().create({
                        "name": filename,
                        "datas": b64,
                        "res_model": "account.move",
                        "res_id": move.id,
                        "mimetype": mimetype,
                    })
                    attach_ids.append(att.id)
            except Exception as e:
                _logger.warning("[FEL_BLOCK_SAFE] Could not build attachments: %s", e)
        try:
            if attach_ids:
                move.message_post(body=body, message_type="comment", attachment_ids=[(4, i) for i in attach_ids])
            else:
                move.message_post(body=body, message_type="comment")
        except Exception as e:
            _logger.warning("[FEL_BLOCK_SAFE] Could not post success message: %s", e)

    def _bb_chatter_timeout(self, move, seconds, extra_html=""):
        cfg = self._bb_cfg()
        if not cfg["chatter_audit"]:
            return
        rid = getattr(move, "fel_request_id", "") or ""
        body = "<b>FEL no recibido</b> en %ss - se aborto el posteo para evitar inconsistencias." % seconds
        if rid:
            body += " Request ID: <code>%s</code>" % rid
        if extra_html:
            body += "<br/><br/><b>Ultima respuesta FEL:</b><br/>" + extra_html
        try:
            move.message_post(body=body, message_type="comment")
        except Exception as e:
            _logger.warning("[FEL_BLOCK_SAFE] Could not post timeout message: %s", e)

    def _bb_wait_fel_or_fail(self):
        cfg = self._bb_cfg()
        if not cfg["block_enabled"]:
            return
        for move in self:
            if not move._bb_needs_fel():
                continue
            if move._bb_has_fel_fields():
                self._bb_chatter_success(move, "")
                continue
            captured, patch = self._bb_capture_http()
            if cfg["call_if_missing"] and hasattr(move, "certificar_megaprint"):
                try:
                    _logger.info("[FEL_BLOCK_SAFE] Trigger certificar_megaprint (missing FEL) move_id=%s", move.id)
                    with patch:
                        move.certificar_megaprint()
                except Exception as e:
                    _logger.warning("[FEL_BLOCK_SAFE] certificar_megaprint() raised: %s", e)
            start = time.time()
            while time.time() - start < cfg["wait_timeout"]:
                self._bb_refresh_fields(move, ["firma_fel","serie_fel","numero_fel"])
                if move._bb_has_fel_fields():
                    _logger.info("[FEL_BLOCK_SAFE] FEL present after wait move_id=%s", move.id)
                    snippet = self._bb_render_http_snippet_html(captured)
                    self._bb_chatter_success(move, snippet)
                    break
                time.sleep(max(1, cfg["poll_seconds"]))
            else:
                snippet_txt = self._bb_render_http_snippet_text(captured) if cfg["include_http_in_popup"] else ""
                msg = _("FEL certification not received within %s seconds; posting aborted.") % cfg["wait_timeout"]
                if snippet_txt:
                    msg += "\n\nLast FEL response:\n%s" % snippet_txt
                # Also try to log to chatter for post-mortem (will rollback with tx but helpful when success)
                snippet_html = self._bb_render_http_snippet_html(captured)
                self._bb_chatter_timeout(move, cfg["wait_timeout"], snippet_html)
                raise UserError(msg)

    def action_post(self):
        res = super().action_post()
        self._bb_wait_fel_or_fail()
        return res

    def write(self, vals):
        posting = "state" in vals and vals.get("state") == "posted"
        res = super().write(vals)
        if posting:
            self._bb_wait_fel_or_fail()
        return res
