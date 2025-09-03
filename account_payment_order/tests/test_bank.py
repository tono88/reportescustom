# © 2017 Creu Blanca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError

from odoo.addons.base.tests.common import BaseCommon


class TestBank(BaseCommon):
    def test_bank(self):
        bank = self.env["res.bank"].search([], limit=1)
        if not bank:
            # This should only happen if we don't have demo data
            bank = (
                self.env["res.bank"]
                .env["res.bank"]
                .create(
                    {
                        "name": "Fiducial Banque",
                        "bic": "FIDCFR21XXX",
                        "street": "38 rue Sergent Michel Berthet",
                        "zip": "69009",
                        "city": "Lyon",
                        "country": self.env.ref("base.fr").id,
                    }
                )
            )
        with self.assertRaises(ValidationError):
            bank.bic = "TEST"
