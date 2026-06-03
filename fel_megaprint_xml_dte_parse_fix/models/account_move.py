# -*- coding: utf-8 -*-

import base64
import html
import logging
import re

from lxml import etree

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _blk_normalize_xml_dte_text(self, xml_text):
        """Return a clean XML string candidate from Megaprint/IFACERe xml_dte.

        The provider can return xml_dte in slightly different shapes depending on
        endpoint/response path: plain XML, escaped XML (&lt;...&gt;), double escaped
        XML, CDATA-wrapped XML or, in some environments, base64-like payloads.
        This helper only normalizes text; it does not change accounting/FEL data.
        """
        if xml_text is None:
            return ""

        if isinstance(xml_text, bytes):
            text = xml_text.decode("utf-8", errors="replace")
        else:
            text = str(xml_text)

        text = text.strip()

        # Strip CDATA wrapper when the text node itself contains it.
        if text.startswith("<![CDATA[") and text.endswith("]]>"):
            text = text[9:-3].strip()

        # Decode escaped XML, including double/triple-escaped responses.
        for _i in range(5):
            unescaped = html.unescape(text).strip()
            if unescaped == text:
                break
            text = unescaped
            if text.startswith("<![CDATA[") and text.endswith("]]>"):
                text = text[9:-3].strip()

        # Some responses include logging/junk before the XML declaration/root.
        # Keep the earliest XML-looking start, preferring XML declaration.
        xml_decl_pos = text.find("<?xml")
        lt_pos = text.find("<")
        if xml_decl_pos > 0:
            text = text[xml_decl_pos:].strip()
        elif lt_pos > 0:
            text = text[lt_pos:].strip()

        # Last-resort: if there is still no XML marker, try base64 decode.
        if "<" not in text:
            compact = re.sub(r"\s+", "", text)
            if compact and re.fullmatch(r"[A-Za-z0-9+/=]+", compact or ""):
                try:
                    decoded = base64.b64decode(compact, validate=True).decode("utf-8", errors="replace").strip()
                    decoded = html.unescape(decoded).strip()
                    if "<" in decoded:
                        text = decoded
                except Exception:
                    pass

        return text

    def _blk_parse_numero_autorizacion_from_regex(self, text):
        """Regex fallback for malformed but readable XML fragments."""
        match = re.search(
            r"<(?:(?P<prefix>[A-Za-z0-9_\-]+):)?NumeroAutorizacion\b(?P<attrs>[^>]*)>"
            r"(?P<firma>.*?)"
            r"</(?:(?P=prefix):)?NumeroAutorizacion>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None

        attrs = match.group("attrs") or ""
        firma = html.unescape(re.sub(r"<[^>]+>", "", match.group("firma") or "")).strip()

        def _attr(name):
            m = re.search(r"\b%s\s*=\s*(['\"])(.*?)\1" % re.escape(name), attrs, flags=re.IGNORECASE | re.DOTALL)
            return html.unescape(m.group(2)).strip() if m else ""

        serie = _attr("Serie") or _attr("serie")
        numero = _attr("Numero") or _attr("numero")

        if not firma and not serie and not numero:
            return None

        return {
            "firma": firma,
            "serie": serie,
            "numero": str(numero).strip(),
        }

    def _fel_parse_na(self, xml_text):
        """Robust parser for NumeroAutorizacion in certified xml_dte.

        Overrides fel_megaprint._fel_parse_na without changing certification
        flow. It accepts namespace variations and escaped xml_dte payloads.
        """
        text = self._blk_normalize_xml_dte_text(xml_text)
        if not text:
            return None

        parser = etree.XMLParser(recover=True, huge_tree=True, remove_blank_text=True)
        root = None
        try:
            root = etree.fromstring(text.encode("utf-8"), parser=parser)
        except Exception as exc:
            _logger.warning("[MEGAPRINT][PARSE_FIX] XML parse failed; trying regex fallback: %s", exc)

        if root is not None:
            # Namespace-agnostic lookup. This works for dte:NumeroAutorizacion,
            # NumeroAutorizacion, or any unexpected prefix.
            nodes = root.xpath("//*[local-name()='NumeroAutorizacion']")
            if nodes:
                na = nodes[0]
                serie = na.get("Serie") or na.get("serie") or ""
                numero = na.get("Numero") or na.get("numero") or ""
                firma = "".join(na.itertext()).strip()

                serie = html.unescape(str(serie or "")).strip()
                numero = html.unescape(str(numero or "")).strip()
                firma = html.unescape(str(firma or "")).strip()

                if firma or serie or numero:
                    return {
                        "firma": firma,
                        "serie": serie,
                        "numero": numero,
                    }

        na = self._blk_parse_numero_autorizacion_from_regex(text)
        if na:
            return na

        _logger.warning(
            "[MEGAPRINT][PARSE_FIX] NumeroAutorizacion not found in xml_dte. Snippet=%s",
            text[:700],
        )
        return None

    def _fel_apply_from_xml(self, factura, xml_certificado_text):
        """Apply NumeroAutorizacion, with safer diagnostics.

        Same external behavior as fel_megaprint: returns True when applied,
        False when NumeroAutorizacion cannot be found/applied. We only add
        robust normalization and log details for diagnosis.
        """
        try:
            na = self._fel_parse_na(xml_certificado_text)
            if not na:
                return False
            self._fel_apply_na(factura, na)
            return True
        except Exception as exc:
            _logger.exception("[MEGAPRINT][PARSE_FIX] Could not apply NumeroAutorizacion: %s", exc)
            return False
