from odoo import Command, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _l10n_ar_rg5329_clean_perception_taxes(self, company):
        """Remove RG 5329 perception taxes from product customer taxes.

        The RG 5329 perception is not a product tax. It is decided dynamically
        on customer invoices, according to partner responsibility and invoice
        taxable base. Keeping it on products makes Odoo bring it always.
        """
        if not self:
            return

        company = company.sudo()
        perception_taxes = company._l10n_ar_rg5329_perception_taxes()
        if not perception_taxes:
            return

        all_company_ids = self.env["res.company"].sudo().search([]).ids
        context = dict(
            self.env.context,
            allowed_company_ids=all_company_ids,
            l10n_ar_rg5329_skip_product_sync=True,
        )

        for template in self.sudo().with_company(company).with_context(context):
            taxes = template.taxes_id - perception_taxes
            if set(taxes.ids) != set(template.taxes_id.ids):
                template.write({"taxes_id": [Command.set(taxes.ids)]})

    def _l10n_ar_rg5329_sync_perception_taxes(self, company):
        """Backward-compatible method used by configuration button.

        It intentionally cleans product taxes instead of assigning perceptions.
        The perception must be applied only on invoices.
        """
        self._l10n_ar_rg5329_clean_perception_taxes(company)
