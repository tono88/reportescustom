# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError
import requests, re
from lxml import etree

NSMAP = {"dte": "http://www.sat.gob.gt/dte/fel/0.2.0"}
_CDATA_XML_DTE_RE = re.compile(r"(<xml_dte><!\[CDATA\[)(.*?)(\]\]></xml_dte>)", re.DOTALL | re.IGNORECASE)

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

        # eliminar Frase 4
        for frase in root.xpath(".//dte:Frase[@TipoFrase='4']", namespaces=NSMAP):
            par = frase.getparent()
            if par is not None:
                par.remove(frase)

        # eliminar impuestos en 0
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

        # totales en 0
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

        # UDM uppercase
        for um in root.xpath(".//dte:Item/dte:UnidadMedida", namespaces=NSMAP):
            if um.text:
                um.text = _as_text(um.text).upper()

        # trim municipios
        for mun in root.xpath(".//dte:DireccionReceptor/dte:Municipio | .//dte:DireccionEmisor/dte:Municipio", namespaces=NSMAP):
            if mun.text:
                mun.text = _as_text(mun.text).strip()

        return etree.tostring(root, encoding="utf-8", xml_declaration=False).decode("utf-8", errors="ignore")
    except Exception:
        return dte_xml

class FelMegaprintPreviewWizard(models.TransientModel):
    _name = "fel.megaprint.preview.wizard"
    _description = "Previsualización del XML FEL"

    move_id = models.Many2one("account.move", required=True)
    endpoint = models.Char("Endpoint", readonly=True)
    xml_text = models.Text("XML (solo lectura)", readonly=True)

    def action_open(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Previsualización XML FEL"),
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_fel_preview_xml(self):
        self.ensure_one()
        original = getattr(super(AccountMove, self), "certificar_megaprint", None)
        if not original:
            raise UserError(_("No se encontró 'certificar_megaprint' del módulo FEL Megaprint."))

        orig_post = requests.post

        def wrapped(url, *args, **kwargs):
            # Capturar body para extraer el DTE del <xml_dte>…
            body = None
            if args and args[0] is not None:
                body = args[0]
            elif "data" in kwargs and kwargs["data"] is not None:
                body = kwargs["data"]
            elif "json" in kwargs and isinstance(kwargs["json"], dict):
                # si viene en JSON, tomarlo directo
                for k in ("xml_dte","xml","dte","xmldte","GTDocumento","gtDocumento","documento","xml_dte_str"):
                    if k in kwargs["json"]:
                        body = kwargs["json"][k]
                        break

            txt = _as_text(body)
            m = _CDATA_XML_DTE_RE.search(txt)
            if m:
                dte = m.group(2)
            else:
                dte = txt  # por si mandan el DTE directo

            # Mostrar el DTE SANITIZADO y detener el flujo
            wiz = self.env["fel.megaprint.preview.wizard"].create({
                "move_id": self.id,
                "endpoint": url or "",
                "xml_text": _sanitize_dte_xml(dte).strip() or _("No se detectó DTE."),
            })
            # restaurar post antes de salir
            requests.post = orig_post
            return wiz.action_open()

        try:
            requests.post = wrapped
            # Llamar el flujo; se detendrá en el primer POST con el wizard
            return original()
        finally:
            requests.post = orig_post
