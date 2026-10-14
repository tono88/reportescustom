"""Data-only packaging and QWeb-expression regressions without a running Odoo."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET
from datetime import date


ROOT = Path(__file__).parents[2] / "l10n_gt_check_printing2_pdf_live"


class Currency:
    name = "GTQ"

    def round(self, value):
        return round(value, 2)

    def with_context(self, **kwargs):
        return self

    def amount_to_text(self, value):
        return "MIL DOSCIENTOS TREINTA Y CUATRO QUETZALES"


@unittest.skipUnless(ROOT.is_dir(), "Las pruebas del paquete importable requieren ambos módulos del repositorio.")
class ImportablePdfTest(unittest.TestCase):
    def setUp(self):
        self.xml = ET.parse(ROOT / "reports/check_reports.xml").getroot()
        self.template = self.xml.find("template[@id='check_document']")
        self.expressions = {t.attrib["t-set"]: t.attrib["t-value"] for t in self.template.iter("t") if "t-set" in t.attrib and "t-value" in t.attrib}

    def values(self, bank="banrural", **changes):
        payment = SimpleNamespace(
            amount=1234.56, state="in_process", payment_type="outbound",
            payment_method_code="check_printing", check_number="000031797",
            partner_id=SimpleNamespace(name="PROVEEDOR DE PRUEBA"),
            currency_id=Currency(), date=date(2026, 10, 14),
        )
        for key, value in changes.items():
            setattr(payment, key, value)
        scope = {"p": payment, "bank_key": bank}
        for key in ("profile", "total_cents", "integer", "cents", "payee", "words", "positions_ok", "valid", "texts"):
            # Match QWeb's expression scope; these are our own source expressions.
            scope[key] = eval(self.expressions[key], {**scope}, scope)
        return scope

    def test_data_only_manifest_and_integer_paper(self):
        manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
        self.assertNotIn("assets", manifest)
        self.assertEqual(list(ROOT.rglob("*.py")), [ROOT / "__manifest__.py"])
        for path in manifest["data"]:
            ET.parse(ROOT / path)
        paper = self.xml.find("record[@model='report.paperformat']")
        for name, value in [("page_width", 165), ("page_height", 70)]:
            self.assertEqual(int(paper.find(f"field[@name='{name}']").text), value)

    def test_both_banks_use_their_own_positions_without_changing_payment(self):
        banrural = self.values()
        gyt = self.values("gyt")
        self.assertTrue(banrural["valid"])
        self.assertTrue(gyt["valid"])
        self.assertEqual(banrural["profile"]["words"][1], 38)
        self.assertEqual(gyt["profile"]["words"][1], 41)
        self.assertEqual(banrural["texts"]["amount"], "1,234.56")
        self.assertTrue(banrural["texts"]["words"].endswith("CON 56/100"))
        self.assertEqual(banrural["p"].check_number, "000031797")
        self.assertEqual(banrural["p"].state, "in_process")

    def test_unassigned_draft_or_wrong_currency_has_no_valid_check(self):
        cases = [
            {"check_number": False}, {"state": "draft"}, {"state": "canceled"},
            {"currency_id": SimpleNamespace(name="USD", round=round, with_context=lambda **kw: Currency())},
            {"payment_type": "inbound"}, {"amount": 0},
            {"partner_id": SimpleNamespace(name="A" * 200)},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertFalse(self.values(**changes)["valid"])

    def test_buttons_use_report_actions_and_existing_fields(self):
        form = ET.parse(ROOT / "views/payment_buttons.xml").getroot()
        buttons = list(form.iter("button"))
        self.assertEqual(len(buttons), 2)
        report_ids = {record.attrib["id"] for record in self.xml.findall("record[@model='ir.actions.report']")}
        for button in buttons:
            self.assertEqual(button.attrib["type"], "action")
            self.assertIn(button.attrib["name"][2:-2], report_ids)
        self.assertFalse(list(form.iter("field"))[-1].findall(".//field[@name='lx350_bank']"))


if __name__ == "__main__":
    unittest.main()
