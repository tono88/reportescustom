"""Data-only packaging and QWeb-expression regressions without a running Odoo."""

import ast
import base64
import struct
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

    def values(self, bank="banrural", context=None, **changes):
        payment = SimpleNamespace(
            amount=1234.56, state="in_process", payment_type="outbound",
            payment_method_code="check_printing", check_number="000031797",
            partner_id=SimpleNamespace(name="PROVEEDOR DE PRUEBA"),
            currency_id=Currency(), date=date(2026, 10, 14),
            env=SimpleNamespace(context=context or {}),
        )
        for key, value in changes.items():
            setattr(payment, key, value)
        scope = {"p": payment, "bank_key": bank}
        for key in ("profile", "amount_adjustment", "adjustment_ok", "total_cents", "integer", "cents", "payee", "words", "texts", "advances", "unit_widths", "positions_ok", "payment_ok", "overflow_keys", "valid"):
            # Match QWeb's expression scope; these are our own source expressions.
            scope[key] = eval(self.expressions[key], {**scope}, scope)
        return scope

    def test_data_only_manifest_and_native_letter_paper(self):
        manifest = ast.literal_eval((ROOT / "__manifest__.py").read_text(encoding="utf-8"))
        assets = manifest["assets"]["web.assets_backend"]
        self.assertEqual(assets, ["l10n_gt_check_printing2_pdf_live/static/src/amount_position.js"])
        self.assertIn("web", manifest["depends"])
        for asset in assets:
            self.assertTrue((ROOT.parent / asset).is_file())
        self.assertEqual(list(ROOT.rglob("*.py")), [ROOT / "__manifest__.py"])
        for path in manifest["data"]:
            ET.parse(ROOT / path)
        paper = self.xml.find("record[@model='report.paperformat']")
        self.assertEqual(paper.find("field[@name='format']").text, "Letter")
        # Native Letter requires zero custom dimensions; mixing both is invalid.
        for name, value in [("page_width", 0), ("page_height", 0)]:
            self.assertEqual(int(paper.find(f"field[@name='{name}']").text), value)

    def test_native_pdf_scale_and_anchor_survive_odoo_article_extraction(self):
        paper = self.xml.find("record[@model='report.paperformat']")
        dpi = int(paper.find("field[@name='dpi']").text)
        self.assertEqual(96 / dpi, 1)
        html = self.template.find("html")
        self.assertEqual(html.attrib["data-report-dpi"], "96")
        article = self.template.find(".//div[@class='article check-page']")
        style = article.attrib["style"]
        for required in ("position:relative", "left:0", "top:0", "width:215.9mm", "height:279mm", "margin:0", "font-family:Arial", "font-weight:bold"):
            self.assertIn(required, style)
        for bank in ("banrural", "gyt"):
            profile = self.values(bank)["profile"]
            x, y, width = profile["amount"]
            self.assertLessEqual(x + width, 162)

    def test_letter_left_origin_avoids_small_page_centering_offset(self):
        # A 165.1 mm PDF centered on 215.9 mm Letter adds 25.4 mm. The new
        # report uses the same Letter canvas as the print driver: no such shift.
        self.assertAlmostEqual((215.9 - 165.1) / 2, 25.4)
        paper = self.xml.find("record[@model='report.paperformat']")
        self.assertEqual(paper.find("field[@name='format']").text, "Letter")
        for bank in ("banrural", "gyt"):
            values = self.values(bank)
            self.assertEqual(values["profile"]["offset_x"], 0)
            self.assertEqual(values["profile"]["offset_y"], 0)
            for key in ("date", "amount", "payee", "words"):
                x, y, width = values["profile"][key]
                self.assertGreaterEqual(x, 3)
                self.assertLessEqual(x + width, 162)
                self.assertLess(y + values['profile']['font_sizes'][key]*25.4/72, 53.85)

    def test_larger_fonts_and_banrural_amount_start_after_currency_symbol(self):
        values = self.values(amount=81689.69)
        profile = values['profile']
        self.assertEqual(profile['amount'], (137, 24, 25))
        self.assertEqual(profile['amount_align'], 'left')
        font_expression = self.expressions['font']
        for key in ('date', 'amount', 'payee', 'words'):
            scope = {**values, 'key': key, 'box': profile[key]}
            font = eval(font_expression, {**scope}, scope)
            self.assertGreaterEqual(font, 9)
            self.assertLessEqual(font, profile['font_sizes'][key])
            if key in ('date', 'payee', 'amount'):
                self.assertEqual(font, 12)
        self.assertEqual(self.values('gyt')['profile']['amount_align'], 'left')
        # The estimate must distinguish wide glyphs after switching to Arial.
        wide = self.values(partner_id=SimpleNamespace(name='W' * 60))
        narrow = self.values(partner_id=SimpleNamespace(name='I' * 60))
        self.assertFalse(wide['valid'])
        self.assertTrue(narrow['valid'])

    def test_both_banks_use_their_own_positions_without_changing_payment(self):
        banrural = self.values()
        gyt = self.values("gyt")
        self.assertTrue(banrural["valid"])
        self.assertTrue(gyt["valid"])
        self.assertEqual(banrural["profile"]["words"][1], 38)
        self.assertEqual(gyt["profile"]["words"][1], 43)
        self.assertEqual(banrural["texts"]["amount"], "1,234.56")
        self.assertTrue(banrural["texts"]["words"].endswith("CON 56/100"))
        self.assertEqual(banrural["p"].check_number, "000031797")
        self.assertEqual(banrural["p"].state, "in_process")

    def test_amount_has_no_extra_shift_and_retains_font_and_box_width(self):
        for bank in ('banrural', 'gyt'):
            values = self.values(bank, amount=81689.69)
            profile = values['profile']
            self.assertTrue(values['valid'])
            for key in ('date', 'amount', 'payee', 'words'):
                box = profile[key]
                scope = {**values, 'key': key, 'box': box}
                x = eval(self.expressions['print_x'], {**scope}, scope)
                base = box[0] + profile['offset_x']
                self.assertEqual(x - base, 0)
                self.assertLessEqual(x + box[2], 162)
                if key == 'amount':
                    self.assertEqual(box[2], 25)
                    self.assertEqual(eval(self.expressions['font'], {**scope}, scope), 12)

    def test_slider_adjusts_only_amount_and_rejects_invalid_context(self):
        for bank in ('banrural', 'gyt'):
            baseline = self.values(bank)
            for shift in (-20, -3.5, 0, 2.5, 20):
                values = self.values(bank, context={'check_amount_shift_x': shift})
                self.assertTrue(values['valid'])
                self.assertEqual(values['texts'], baseline['texts'])
                for key in ('date', 'amount', 'payee', 'words'):
                    scope = {**values, 'key': key, 'box': values['profile'][key]}
                    x = eval(self.expressions['print_x'], dict(scope), scope)
                    self.assertEqual(x - scope['box'][0], shift if key == 'amount' else 0)
            for shift in (-21, 21, '5', None, float('nan'), float('inf'), {}, []):
                with self.subTest(bank=bank, shift=shift):
                    self.assertFalse(self.values(bank, context={'check_amount_shift_x': shift})['valid'])

    def test_bank_buttons_open_slider_and_keep_existing_report_actions(self):
        view = ET.parse(ROOT / 'views/payment_buttons.xml').getroot()
        for bank in ('banrural', 'gyt'):
            client = view.find(f"record[@id='action_adjust_{bank}']")
            self.assertEqual(client.get('model'), 'ir.actions.client')
            self.assertEqual(client.find("field[@name='tag']").text,
                             'l10n_gt_check_printing2_pdf_live.amount_position')
            self.assertEqual(ast.literal_eval(client.find("field[@name='params']").get('eval')), {'bank': bank})
            button = view.find(f".//button[@name='%(action_adjust_{bank})d']")
            self.assertIsNotNone(button)
            self.assertIn('check_number', button.get('invisible'))
            self.assertIsNotNone(self.xml.find(f"record[@id='action_{bank}']"))

    def test_unassigned_draft_or_wrong_currency_has_no_valid_check(self):
        cases = [
            {"check_number": False}, {"state": "draft"}, {"state": "canceled"}, {"date": False},
            {"currency_id": SimpleNamespace(name="USD", round=round, with_context=lambda **kw: Currency())},
            {"payment_type": "inbound"}, {"amount": 0},
            {"amount": 12345678901234.56},
            {"partner_id": SimpleNamespace(name="A" * 200)},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertFalse(self.values(**changes)["valid"])

    def test_plural_quetzales_fits_gyt_without_suppressing_real_overflow(self):
        class ActualCurrency(Currency):
            def amount_to_text(self, value):
                return 'OCHENTA Y UN MIL SEISCIENTOS OCHENTA Y NUEVE QUETZALES'

        for bank in ('banrural', 'gyt'):
            values = self.values(bank, amount=81689.69, currency_id=ActualCurrency())
            self.assertTrue(values['valid'])
            self.assertEqual(values['overflow_keys'], [])
            estimate = values['unit_widths']['words'] * 9 + len(values['texts']['words']) * 0.12
            self.assertLessEqual(estimate, 138)
        overflow = self.values('gyt', partner_id=SimpleNamespace(name='W' * 60))
        self.assertTrue(overflow['payment_ok'])
        self.assertFalse(overflow['valid'])
        self.assertEqual(overflow['overflow_keys'], ['payee'])

    def test_buttons_use_client_actions_and_existing_fields(self):
        form = ET.parse(ROOT / "views/payment_buttons.xml").getroot()
        buttons = list(form.iter("button"))
        self.assertEqual(len(buttons), 2)
        action_ids = {record.attrib["id"] for record in form.findall("record[@model='ir.actions.client']")}
        for button in buttons:
            self.assertEqual(button.attrib["type"], "action")
            self.assertIn(button.attrib["name"][2:-2], action_ids)
        self.assertFalse(list(form.iter("field"))[-1].findall(".//field[@name='lx350_bank']"))

    def test_graphic_amount_keeps_every_digit_and_separator_in_its_box(self):
        glyphs = ast.literal_eval(self.expressions['amount_glyphs'])
        self.assertEqual(set(glyphs), set('0123456789,.'))
        self.assertEqual(len(set(glyphs.values())), 12)
        for char, encoded in glyphs.items():
            data = base64.b64decode(encoded, validate=True)
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            width, height = struct.unpack('>II', data[16:24])
            self.assertEqual(height, 128)
            self.assertEqual(width, 71 if char.isdigit() else 36)
        graphic = self.template.find(".//div[@class='check-amount-graphic']")
        self.assertIsNotNone(graphic)
        self.assertFalse(list(graphic.iterfind('.//*[@t-out]')))
        image = graphic.find('.//img')
        self.assertEqual(image.get('t-att-alt'), 'amount_char')
        for amount in (1578.85, 81689.69, 1234567.89):
            values = self.values('gyt', amount=amount)
            box = values['profile']['amount']
            scope = {**values, 'key': 'amount', 'box': box, 'amount_glyphs': glyphs}
            scope['font'] = eval(self.expressions['font'], dict(scope), scope)
            previous_end = 0
            for index, char in enumerate(values['texts']['amount']):
                scope.update(amount_char=char, amount_char_index=index)
                x = eval(self.expressions['glyph_x'], dict(scope), scope)
                scope['glyph_x'] = x
                src = eval(image.get('t-att-src'), dict(scope), scope)
                self.assertEqual(src, 'data:image/png;base64,' + glyphs[char])
                self.assertGreaterEqual(x+1e-9, previous_end)
                previous_end = x + values['advances'][char]*scope['font']*25.4/72000
            self.assertLessEqual(previous_end, box[2])


if __name__ == "__main__":
    unittest.main()
