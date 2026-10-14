import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("check_geometry", Path(__file__).parents[1] / "layout.py")
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)


class CheckGeometryTest(unittest.TestCase):
    def test_centavos_do_not_overflow_or_change_spanish_tens(self):
        self.assertEqual(layout.amount_parts(82482.73), (82482, 73))
        self.assertEqual(layout.amount_parts(1.999), (2, 0))
        self.assertEqual(layout.amount_parts(0.005), (0, 1))
        self.assertEqual(layout.amount_parts(0), (0, 0))
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                layout.amount_parts(value)

    def test_real_size_and_initial_geometry(self):
        self.assertEqual(layout.LAYOUTS[layout.PERSONAL], 165.10)
        self.assertEqual(layout.LAYOUTS[layout.GYT], 165.10)
        self.assertEqual(layout.HEIGHT, 69.85)
        for positions in layout.INITIAL_POSITIONS.values():
            layout.validate_geometry(165.1, positions, 9)

    def test_bank_buttons_cannot_select_the_other_bank(self):
        layout.require_bank(layout.PERSONAL, "banrural")
        layout.require_bank(layout.GYT, "gyt")
        for report, bank in [(layout.PERSONAL, "gyt"), (layout.GYT, "banrural"), ("unknown", "gyt")]:
            with self.subTest(report=report, bank=bank), self.assertRaises(ValueError):
                layout.require_bank(report, bank)

    def test_two_bank_actions_reference_personal_paper_and_separate_buttons(self):
        import xml.etree.ElementTree as ET
        root = Path(__file__).parents[1]
        reports = ET.parse(root / "reports/report_check.xml").getroot()
        records = {record.attrib["id"]: record for record in reports.findall("record")}
        for bank in ("personal", "gyt"):
            paper = records[f"paperformat_{bank}"]
            # Match Odoo's Integer conversion; float() hid the original bug.
            self.assertEqual(int(paper.find("field[@name='page_width']").text), layout.PAPER_WIDTH)
            self.assertEqual(int(paper.find("field[@name='page_height']").text), layout.PAPER_HEIGHT)
            report = records[f"action_check_{bank}"]
            self.assertEqual(report.find("field[@name='paperformat_id']").attrib["ref"], f"paperformat_{bank}")
        form = ET.parse(root / "views/account_payment_views.xml").getroot()
        for bank in ("banrural", "gyt"):
            button = form.find(f".//button[@name='action_lx350_print_{bank}_usb']")
            self.assertIsNotNone(button)
            self.assertIn(f"lx350_bank != '{bank}'", button.attrib["invisible"])

    def test_outside_paper_or_micr_is_refused(self):
        for box in [(2, 24, 100), (18, 3, 100), (139, 24, 30), (18, 53, 100), (float("nan"), 24, 100)]:
            with self.subTest(box=box), self.assertRaises(ValueError):
                layout.validate_geometry(165.1, {"field": box}, 9)

    def test_long_text_is_never_silently_cut(self):
        self.assertEqual(layout.fit_font("BENEFICIARIO", 144, 9), 9)
        self.assertGreaterEqual(layout.fit_font("A" * 70, 144, 9), 7)
        with self.assertRaises(ValueError):
            layout.fit_font("A" * 200, 144, 9)


if __name__ == "__main__":
    unittest.main()
