from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import UserError
from odoo.tests import tagged

from ..layout import COMMERCIAL, PERSONAL


@tagged("post_install", "-at_install")
class TestCheckReports(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data["default_journal_bank"]
        cls.journal.bank_check_printing_layout = PERSONAL

    def test_calibration_renders_html_without_payments_or_numbering(self):
        report = self.env.ref("l10n_gt_check_printing2_lx350.action_calibration_personal")
        sequence_before = self.journal.check_sequence_id.number_next_actual
        payment_count = self.env["account.payment"].search_count([])
        html, _ = report._render_qweb_html(report.report_name, self.journal.ids)
        self.assertIn(b"BENEFICIARIO DE PRUEBA", html)
        self.assertIn(b"PRUEBA SIN VALOR", html)
        self.assertIn(b"165.1mm", html)
        self.assertEqual(self.journal.check_sequence_id.number_next_actual, sequence_before)
        self.assertEqual(self.env["account.payment"].search_count([]), payment_count)

    def test_journal_layout_precedes_company_layout(self):
        self.journal.company_id.account_check_printing_layout = "l10n_gt_check_printing2.check_top"
        self.assertEqual(self.journal._lx350_layout(), PERSONAL)

    def test_calibration_rejects_wrong_report_size(self):
        self.journal.bank_check_printing_layout = COMMERCIAL
        model = self.env["report.l10n_gt_check_printing2_lx350.calibration_personal"]
        with self.assertRaises(UserError):
            model._get_report_values(self.journal.ids)
        commercial = self.env["report.l10n_gt_check_printing2_lx350.calibration_commercial"]
        self.assertEqual(commercial._get_report_values(self.journal.ids)["width"], 190.5)

    def test_position_over_magnetic_band_is_rejected(self):
        self.journal.lx350_offset_y = 20
        with self.assertRaises(UserError):
            self.journal.action_lx350_calibration()

    def test_print_preference_does_not_change_other_journal(self):
        other = self.journal.copy({"name": "Otra cuenta", "code": "LX2"})
        self.journal.lx350_offset_x = -2
        self.assertEqual(other.lx350_offset_x, 0)

    def test_usb_calibration_has_no_payment_number_context(self):
        action = self.journal.action_lx350_calibration_usb()
        self.assertTrue(action["lx350"]["direct"])
        self.assertTrue(action["lx350"]["calibration"])
        self.assertEqual(action["context"]["active_ids"], self.journal.ids)
        self.assertNotIn("payment_ids", action["context"])
