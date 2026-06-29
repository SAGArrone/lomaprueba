import unittest

from odoo import Command
from odoo.tests.common import TransactionCase


class TestRG5329Perception(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.tax_group = cls.env["account.tax.group"].search([], limit=1)
        cls.account = cls.env["account.account"].search(
            [("deprecated", "=", False)],
            limit=1,
        )
        cls.responsibility = cls.env["l10n_ar.afip.responsibility.type"].search(
            [("name", "ilike", "Responsable Inscripto")],
            limit=1,
        )
        if not cls.tax_group or not cls.account or not cls.responsibility:
            raise unittest.SkipTest("La base de test no tiene localizacion contable argentina completa.")

        cls.vat21 = cls.env["account.tax"].create(
            {
                "name": "IVA 21% RG5329 Test",
                "amount_type": "percent",
                "amount": 21.0,
                "type_tax_use": "sale",
                "company_id": cls.company.id,
                "tax_group_id": cls.tax_group.id,
            }
        )
        cls.vat105 = cls.env["account.tax"].create(
            {
                "name": "IVA 10,5% RG5329 Test",
                "amount_type": "percent",
                "amount": 10.5,
                "type_tax_use": "sale",
                "company_id": cls.company.id,
                "tax_group_id": cls.tax_group.id,
            }
        )
        cls.category = cls.env["product.category"].create({"name": "RG5329 Test"})
        cls.company.write(
            {
                "l10n_ar_rg5329_account_id": cls.account.id,
                "l10n_ar_rg5329_tax_group_id": cls.tax_group.id,
                "l10n_ar_rg5329_min_amount": 3000.0,
                "l10n_ar_rg5329_responsibility_type_ids": [Command.set(cls.responsibility.ids)],
                "l10n_ar_rg5329_product_categ_ids": [Command.set(cls.category.ids)],
                "l10n_ar_rg5329_enabled": True,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Cliente RG5329 Test",
                "l10n_ar_afip_responsibility_type_id": cls.responsibility.id,
            }
        )

    def _product(self, name, tax):
        return self.env["product.product"].create(
            {
                "name": name,
                "categ_id": self.category.id,
                "taxes_id": [Command.set(tax.ids)],
            }
        )

    def _invoice(self, product, amount):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1.0,
                            "price_unit": amount,
                            "tax_ids": [Command.set(product.taxes_id.ids)],
                        }
                    )
                ],
            }
        )

    def test_product_gets_3_percent_perception_for_vat_21(self):
        product = self._product("Producto IVA 21 RG5329", self.vat21)
        perception_tax = product.taxes_id.filtered(
            lambda tax: tax.l10n_ar_rg5329_perception and tax.l10n_ar_rg5329_vat_rate == "vat_21"
        )
        self.assertEqual(len(perception_tax), 1)

    def test_invoice_removes_perception_below_minimum(self):
        product = self._product("Producto bajo minimo RG5329", self.vat21)
        invoice = self._invoice(product, 90000.0)
        perception_taxes = invoice.invoice_line_ids.tax_ids.filtered("l10n_ar_rg5329_perception")
        self.assertFalse(perception_taxes)

    def test_invoice_applies_perception_above_minimum(self):
        product = self._product("Producto sobre minimo RG5329", self.vat21)
        invoice = self._invoice(product, 110000.0)
        perception_taxes = invoice.invoice_line_ids.tax_ids.filtered("l10n_ar_rg5329_perception")
        self.assertEqual(perception_taxes.l10n_ar_rg5329_vat_rate, "vat_21")

    def test_invoice_uses_aggregate_base_for_vat_10_5(self):
        product = self._product("Producto IVA 10,5 RG5329", self.vat105)
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1.0,
                            "price_unit": 110000.0,
                            "tax_ids": [Command.set(product.taxes_id.ids)],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1.0,
                            "price_unit": 110000.0,
                            "tax_ids": [Command.set(product.taxes_id.ids)],
                        }
                    ),
                ],
            }
        )
        perception_taxes = invoice.invoice_line_ids.tax_ids.filtered("l10n_ar_rg5329_perception")
        self.assertEqual(perception_taxes.l10n_ar_rg5329_vat_rate, "vat_10_5")
