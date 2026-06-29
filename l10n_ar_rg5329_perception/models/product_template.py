from odoo import Command, api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        if not self.env.context.get("l10n_ar_rg5329_skip_product_sync"):
            templates._l10n_ar_rg5329_sync_configured_companies()
        return templates

    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get("l10n_ar_rg5329_skip_product_sync"):
            return res

        if "categ_id" in vals or "taxes_id" in vals:
            self._l10n_ar_rg5329_sync_configured_companies()
        return res

    def _l10n_ar_rg5329_sync_configured_companies(self):
        companies = self.env["res.company"].sudo().search([])
        for company in companies:
            self._l10n_ar_rg5329_sync_perception_taxes(company)

    def _l10n_ar_rg5329_sync_perception_taxes(self, company):
        if not self:
            return

        company = company.sudo()
        all_company_ids = self.env["res.company"].sudo().search([]).ids
        context = dict(
            self.env.context,
            allowed_company_ids=all_company_ids,
            l10n_ar_rg5329_skip_product_sync=True,
        )

        for template in self.sudo().with_company(company).with_context(context):
            taxes = company._l10n_ar_rg5329_base_taxes(template.taxes_id)
            if set(taxes.ids) != set(template.taxes_id.ids):
                template.write({"taxes_id": [Command.set(taxes.ids)]})
