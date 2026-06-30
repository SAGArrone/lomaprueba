from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        if not self.env.context.get("l10n_ar_rg5329_skip_product_sync"):
            templates._l10n_ar_rg5329_sync_configured_companies()
        return templates

    def write(self, vals):
        old_rate_by_company = {}
        companies = self.env["res.company"].sudo().search([])
        should_track_tax_change = (
            "taxes_id" in vals
            and "categ_id" not in vals
            and not self.env.context.get("l10n_ar_rg5329_skip_product_sync")
        )
        if should_track_tax_change:
            for template in self.sudo():
                old_rate_by_company[template.id] = {}
                for company in companies:
                    taxes = company._l10n_ar_rg5329_base_taxes(
                        template.with_company(company).taxes_id
                    )
                    old_rate_by_company[template.id][company.id] = (
                        company._l10n_ar_rg5329_rate_key_from_taxes(taxes)
                    )

        res = super().write(vals)

        if self.env.context.get("l10n_ar_rg5329_skip_product_sync"):
            return res

        if "categ_id" in vals:
            self._l10n_ar_rg5329_sync_configured_companies()
        elif "taxes_id" in vals:
            for company in companies:
                templates_to_sync = self.sudo().browse()
                for template in self.sudo():
                    taxes = company._l10n_ar_rg5329_base_taxes(
                        template.with_company(company).taxes_id
                    )
                    new_rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(taxes)
                    old_rate_key = old_rate_by_company.get(template.id, {}).get(company.id)
                    if old_rate_key != new_rate_key:
                        templates_to_sync |= template
                templates_to_sync._l10n_ar_rg5329_sync_perception_taxes(company)
        return res

    def _l10n_ar_rg5329_sync_configured_companies(self):
        companies = self.env["res.company"].sudo().search([])
        for company in companies:
            self._l10n_ar_rg5329_sync_perception_taxes(company)

    def _l10n_ar_rg5329_sync_perception_taxes(self, company):
        if not self:
            return

        company = company.sudo()
        tax_by_rate = company._l10n_ar_rg5329_perception_tax_by_rate()
        reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()
        all_company_ids = self.env["res.company"].sudo().search([]).ids
        context = dict(
            self.env.context,
            allowed_company_ids=all_company_ids,
            l10n_ar_rg5329_skip_product_sync=True,
        )

        for template in self.sudo().with_company(company).with_context(context):
            taxes = company._l10n_ar_rg5329_base_taxes(template.taxes_id)
            should_apply = (
                company._l10n_ar_rg5329_has_required_configuration()
                and template.categ_id.id in reached_category_ids
            )
            if should_apply:
                rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(taxes)
                if rate_key and tax_by_rate.get(rate_key):
                    taxes |= tax_by_rate[rate_key]
            if set(taxes.ids) != set(template.taxes_id.ids):
                template.write({"taxes_id": [(6, 0, taxes.ids)]})
