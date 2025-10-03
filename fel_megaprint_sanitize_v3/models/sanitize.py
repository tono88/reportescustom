# -*- coding: utf-8 -*-
from odoo import models
import requests, re
from lxml import etree

NSMAP = {"dte":"http://www.sat.gob.gt/dte/fel/0.2.0", "ds":"http://www.w3.org/2000/09/xmldsig#"}
CDATA_XML_DTE_RE = re.compile(r"(<xml_dte><!\[CDATA\[)(.*?)(\]\]></xml_dte>)", re.DOTALL | re.IGNORECASE)

def _as_text(x):
    if x is None:
        return ""
    if isinstance(x, bytes):
        try:
            return x.decode("utf-8", errors="ignore")
        except Exception:
            return repr(x)
    return str(x)

def _sanitize_dte_xml(dte_xml: str) -> str:
    if not dte_xml:
        return dte_xml
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(_as_text(dte_xml).encode("utf-8", errors="ignore"), parser=parser)

        # Quitar Frase 4
        for frase in root.xpath(".//dte:Frase[@TipoFrase='4']", namespaces=NSMAP):
            par = frase.getparent()
            if par is not None:
                par.remove(frase)

        # Impuestos en cero (por Item)
        for imp in root.xpath(".//dte:Item/dte:Impuestos/dte:Impuesto", namespaces=NSMAP):
            m = imp.find("dte:MontoImpuesto", namespaces=NSMAP)
            if m is not None:
                try:
                    val = float((_as_text(m.text) or "0").strip())
                except Exception:
                    val = 0.0
                if val == 0.0:
                    par = imp.getparent()
                    if par is not None:
                        par.remove(imp)

        # Totales en cero
        for t in root.xpath(".//dte:Totales/dte:TotalImpuestos/dte:TotalImpuesto", namespaces=NSMAP):
            try:
                val = float((t.get("TotalMontoImpuesto") or "0").strip())
            except Exception:
                val = 0.0
            if val == 0.0:
                par = t.getparent()
                if par is not None:
                    par.remove(t)
                if par is not None and len(par) == 0:
                    gpar = par.getparent()
                    if gpar is not None:
                        gpar.remove(par)

        # UDM en mayúsculas
        for um in root.xpath(".//dte:Item/dte:UnidadMedida", namespaces=NSMAP):
            if um.text:
                um.text = _as_text(um.text).upper()

        # Trim municipios
        for mun in root.xpath(".//dte:DireccionReceptor/dte:Municipio | .//dte:DireccionEmisor/dte:Municipio", namespaces=NSMAP):
            if mun.text:
                mun.text = _as_text(mun.text).strip()

        return etree.tostring(root, encoding="utf-8", xml_declaration=False).decode("utf-8", errors="ignore")
    except Exception:
        return dte_xml

def _sanitize_request_body_pre_sign(url, body: str):
    """Sanea SOLO si el endpoint es solicitaFirma y el DTE NO está firmado (sin <ds:Signature>)."""
    if "solicitaFirma" not in (url or ""):
        return body
    txt = _as_text(body)
    m = CDATA_XML_DTE_RE.search(txt)
    if m:
        dte = m.group(2)
        if "<ds:Signature" in dte:
            return body  # ya firmado, no tocar
        cleaned = _sanitize_dte_xml(dte)
        return txt[:m.start(2)] + cleaned + txt[m.end(2):]
    # si el body es el DTE directo
    if "<ds:Signature" in txt:
        return body
    return _sanitize_dte_xml(txt)

class AccountMove(models.Model):
    _inherit = "account.move"

    def certificar_megaprint(self):
        """Envuelve la certificación para sanear SOLO antes de firmar. Nunca toca XML firmado."""
        self.ensure_one()
        original = getattr(super(AccountMove, self), "certificar_megaprint", None)
        if not original:
            return super(AccountMove, self).certificar_megaprint()

        orig_post = requests.post
        def wrapped(url, *args, **kwargs):
            url = url or ""
            # data en kwargs
            if "data" in kwargs and isinstance(kwargs["data"], (str, bytes)):
                new_data = _sanitize_request_body_pre_sign(url, kwargs["data"])
                if isinstance(new_data, str):
                    new_data = new_data.encode("utf-8")
                kwargs["data"] = new_data
            # cuerpo en args[0]
            elif args and isinstance(args[0], (str, bytes)):
                new0 = _sanitize_request_body_pre_sign(url, args[0])
                if isinstance(new0, str):
                    new0 = new0.encode("utf-8")
                args = (new0,) + tuple(args[1:])
            # json con xml embebido
            if "json" in kwargs and isinstance(kwargs["json"], dict) and "solicitaFirma" in url:
                for k in ("xml_dte","xml","dte","xmldte","GTDocumento","gtDocumento","documento","xml_dte_str"):
                    if k in kwargs["json"]:
                        val = kwargs["json"][k]
                        if "<ds:Signature" not in _as_text(val):
                            kwargs["json"][k] = _sanitize_dte_xml(val)
                        break
            return orig_post(url, *args, **kwargs)

        try:
            requests.post = wrapped
            return original()
        finally:
            requests.post = orig_post
