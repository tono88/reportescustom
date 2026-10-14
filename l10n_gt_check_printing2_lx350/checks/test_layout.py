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
        self.assertEqual(layout.HEIGHT, 69.85)
        layout.validate_geometry(165.1, {"date": (18, 24, 110), "amount": (139, 24, 23), "words": (18, 38, 144)}, 9)

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
