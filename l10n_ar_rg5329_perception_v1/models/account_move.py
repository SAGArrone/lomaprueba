from odoo import Command, api, fields, models
from odoo.tools import float_compare

from .res_company import RG5329_TAX_SPECS


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange(
        "invoice_line_ids",
        "invoice_line_ids.product_id",
        "invoice_line_ids.quantity",
        "invoice_line_ids.price_unit",
        "invoice_line_ids.discount",
        "invoice_line_ids.tax_ids",
        "partner_id",
        "move_type",
        "company_id",
        "fiscal_position_id",
    )
    def _onchange_l10n_ar_rg5329_sync_invoice_taxes(self):
        self._l10n_ar_rg5329_sync_invoice_taxes()

    def write(self, vals):
        res = super().write(vals)
        watched_fields = {
            "invoice_line_ids",
            "partner_id",
            "move_type",
            "company_id",
            "fiscal_position_id",
        }
        if watched_fields.intersection(vals) and not self.env.context.get(
            "l10n_ar_rg5329_skip_invoice_sync"
        ):
            self._l10n_ar_rg5329_sync_invoice_taxes()
        return res

    def _l10n_ar_rg5329_can_apply(self):
        self.ensure_one()
        company = self.company_id
        return (
            self.state == "draft"
            and self.move_type == "out_invoice"
            and company.l10n_ar_rg5329_enabled
            and company._l10n_ar_rg5329_is_partner_reached(self.partner_id)
        )

    def _l10n_ar_rg5329_base_by_rate(self):
        self.ensure_one()
        company = self.company_id
        reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()
        perception_taxes = company._l10n_ar_rg5329_perception_taxes()

        bases = {rate_key: 0.0 for rate_key in RG5329_TAX_SPECS}

        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type):
            if not line.product_id:
                continue

            if line.product_id.categ_id.id not in reached_category_ids:
                continue

            taxes_without_perception = line.tax_ids - perception_taxes
            rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(
                taxes_without_perception
            )

            if rate_key:
                bases[rate_key] += line.price_subtotal

        return bases

    def _l10n_ar_rg5329_applicable_rate_keys(self):
        self.ensure_one()

        if not self._l10n_ar_rg5329_can_apply():
            return set()

        invoice_currency = self.currency_id or self.company_currency_id
        company_currency = self.company_id.currency_id
        conversion_date = self.invoice_date or fields.Date.context_today(self)

        applicable = set()

        for rate_key, base in self._l10n_ar_rg5329_base_by_rate().items():
            perception_amount = invoice_currency.round(
                base * RG5329_TAX_SPECS[rate_key]["amount"] / 100.0
            )

            perception_amount_company = company_currency.round(
                invoice_currency._convert(
                    perception_amount,
                    company_currency,
                    self.company_id,
                    conversion_date,
                )
            )

            if (
                float_compare(
                    perception_amount_company,
                    self.company_id.l10n_ar_rg5329_min_amount,
                    precision_rounding=company_currency.rounding,
                )
                > 0
            ):
                applicable.add(rate_key)

        return applicable

    def _l10n_ar_rg5329_sync_invoice_taxes(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue

            company = move.company_id
            perception_taxes = company._l10n_ar_rg5329_perception_taxes()

            if company.l10n_ar_rg5329_enabled:
                company._l10n_ar_rg5329_ensure_taxes()
                perception_taxes = company._l10n_ar_rg5329_perception_taxes()

            tax_by_rate = company._l10n_ar_rg5329_perception_tax_by_rate()
            reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()
            applicable_rate_keys = move._l10n_ar_rg5329_applicable_rate_keys()

            for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                taxes = line.tax_ids - perception_taxes

                should_apply = (
                    move._l10n_ar_rg5329_can_apply()
                    and line.product_id
                    and line.product_id.categ_id.id in reached_category_ids
                )

                if should_apply:
                    rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(taxes)
                    perception_tax = tax_by_rate.get(rate_key)

                    if rate_key in applicable_rate_keys and perception_tax:
                        taxes |= perception_tax

                if set(taxes.ids) != set(line.tax_ids.ids):
                    line.with_context(
                        l10n_ar_rg5329_skip_invoice_sync=True
                    ).tax_ids = [Command.set(taxes.ids)]
