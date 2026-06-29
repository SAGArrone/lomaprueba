from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
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

    def action_post(self):
        self._l10n_ar_rg5329_sync_invoice_taxes()
        return super().action_post()

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
                taxes_without_perception = line.tax_ids - perception_taxes
                rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(
                    taxes_without_perception
                )

                raise ValidationError(
                    "DEBUG RG5329\n"
                    f"Regimen habilitado: {company.l10n_ar_rg5329_enabled}\n"
                    f"Cliente: {move.partner_id.display_name}\n"
                    f"Responsabilidad cliente: "
                    f"{move.partner_id.commercial_partner_id.l10n_ar_afip_responsibility_type_id.display_name}\n"
                    f"Cliente alcanzado: {company._l10n_ar_rg5329_is_partner_reached(move.partner_id)}\n"
                    f"Categorias configuradas: {company.l10n_ar_rg5329_product_categ_ids.mapped('display_name')}\n"
                    f"Categoria producto: {line.product_id.categ_id.display_name}\n"
                    f"Categoria ID producto: {line.product_id.categ_id.id}\n"
                    f"Categorias alcanzadas IDs: {company._l10n_ar_rg5329_reached_category_ids()}\n"
                    f"Impuestos linea: {line.tax_ids.mapped('name')}\n"
                    f"Impuestos sin RG: {taxes_without_perception.mapped('name')}\n"
                    f"Rate detectado: {rate_key}\n"
                    f"Base linea: {line.price_subtotal}\n"
                    f"Bases por tasa: {move._l10n_ar_rg5329_base_by_rate()}\n"
                    f"Rate keys aplicables: {applicable_rate_keys}\n"
                    f"Impuestos RG: {company._l10n_ar_rg5329_perception_taxes().mapped('name')}\n"
                    f"Tax by rate: { {k: v.mapped('name') for k, v in tax_by_rate.items()} }"
                )

                taxes = taxes_without_perception

                should_apply = (
                    move._l10n_ar_rg5329_can_apply()
                    and line.product_id
                    and line.product_id.categ_id.id in reached_category_ids
                )

                if should_apply and rate_key:
                    perception_tax = tax_by_rate.get(rate_key)
                    if rate_key in applicable_rate_keys and perception_tax:
                        taxes |= perception_tax

                if set(taxes.ids) != set(line.tax_ids.ids):
                    line.with_context(
                        l10n_ar_rg5329_skip_invoice_sync=True
                    ).tax_ids = taxes
