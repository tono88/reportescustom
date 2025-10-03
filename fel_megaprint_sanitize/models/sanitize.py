
# -*- coding: utf-8 -*-
from odoo import models, api
import requests
from lxml import etree

DESIRED_ENDPOINTS = ("solicitaFirma", "registrarDocumentoXML")

NSMAP = {
    "dte": "http://www.sat.gob.gt/dte/fel/0.2.0",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

def _as_text(x):
    if x is None:
        return ""
    if isinstance(x, bytes):
        try:
            return x.decode("utf-8", errors="ignore")
        except Exception:
            return repr(x)
    return str(x)

def _sanitize_xml(xml_str: str) -> str:
    if not xml_str:
        return xml_str
    try:
        parser = etree.XMLParser(remove_blank_text=True)
        root = etree.fromstring(_as_text(xml_str).encode("utf-8", errors="ignore"), parser=parser)

        # 1) Eliminar Frase TipoFrase="4"
        for frase in root.xpath(".//dte:Frase[@TipoFrase='4']", namespaces=NSMAP):
            parent = frase.getparent()
            if parent is not None:
                parent.remove(frase)

        # 2) Eliminar Impuestos en cero dentro de cada Item
        for imp in root.xpath(".//dte:Item/dte:Impuestos/dte:Impuesto", namespaces=NSMAP):
            monto = imp.find("dte:MontoImpuesto", namespaces=NSMAP)
            if monto is not None:
                try:
                    val = float(_as_text(monto.text).strip() or "0")
                except Exception:
                    val = 0.0
                if val == 0.0:
                    parent = imp.getparent()
                    if parent is not None:
                        parent.remove(imp)

        # 3) Eliminar Totales/TotalImpuesto con total 0
        for t in root.xpath(".//dte:Totales/dte:TotalImpuestos/dte:TotalImpuesto", namespaces=NSMAP):
            total_attr = t.get("TotalMontoImpuesto", "0").strip()
            try:
                val = float(total_attr or "0")
            except Exception:
                val = 0.0
            if val == 0.0:
                parent = t.getparent()
                if parent is not None:
                    parent.remove(t)

        return etree.tostring(root, encoding="utf-8", xml_declaration=False).decode("utf-8", errors="ignore")
    except Exception:
        # Si por alguna razón no podemos parsear, devolvemos original
        return xml_str

class AccountMove(models.Model):
    _inherit = "account.move"

    def _fel_wrap_post(self):
        """Devuelve un wrapper de requests.post que inyecta saneamiento de XML en endpoints objetivo."""
        orig_post = requests.post

        def wrapped(url, *args, **kwargs):
            url = url or ""
            # Identificar si es uno de los endpoints a los que modificaremos el XML
            is_target = any(ep in url for ep in DESIRED_ENDPOINTS)
            if is_target:
                # El DTE suele ir en json['xml'] o json['xml_dte'] o data['xml'] o en files
                json_data = kwargs.get("json")
                data_kw = kwargs.get("data")
                files = kwargs.get("files")

                def sanitize_inplace(value):
                    if isinstance(value, dict):
                        for key in ("xml_dte", "xml", "dte", "xmldte", "GTDocumento", "gtDocumento", "documento", "xml_dte_str"):
                            if key in value and isinstance(value[key], (str, bytes)):
                                value[key] = _sanitize_xml(value[key])
                    return value

                if isinstance(json_data, dict):
                    kwargs["json"] = sanitize_inplace(json_data.copy())
                elif isinstance(data_kw, dict):
                    kwargs["data"] = sanitize_inplace(data_kw.copy())
                elif files:
                    # Si viene como archivo, intentar interceptar ('name.xml', content, mime)
                    if isinstance(files, dict):
                        new_files = {}
                        for k, v in files.items():
                            if isinstance(v, (tuple, list)) and len(v) >= 2:
                                name, content = v[0], v[1]
                                new_files[k] = (name, _sanitize_xml(content), v[2] if len(v) > 2 else "application/xml")
                            else:
                                new_files[k] = v
                        kwargs["files"] = new_files

                # Si el cuerpo es el primer arg (raw xml/string)
                if args:
                    body = args[0]
                    if isinstance(body, (str, bytes)):
                        args = (_sanitize_xml(body),) + args[1:]

            return orig_post(url, *args, **kwargs)

        return orig_post, wrapped

    def certificar_megaprint(self):
        """Envuelve la certificación original para sanear el DTE antes de enviarlo."""
        self.ensure_one()
        original = getattr(super(AccountMove, self), "certificar_megaprint", None)
        if not original:
            # Si no existe, no hacemos nada especial
            return super(AccountMove, self).certificar_megaprint()

        orig_post, wrapped = self._fel_wrap_post()
        try:
            requests.post = wrapped
            return original()
        finally:
            requests.post = orig_post
