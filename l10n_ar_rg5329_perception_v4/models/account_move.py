import logging

from odoo import api, fields, models
from odoo.tools import float_compare

from .res_company import RG5329_TAX_SPECS


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

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

    def _l10n_ar_rg5329_invoice_product_lines(self):
        self.ensure_one()
        lines = self.invoice_line_ids.filtered(
            lambda line: not line.display_type and line.product_id
        )
        if not lines:
            lines = self.line_ids.filtered(
                lambda line: (
                    not line.display_type
                    and line.product_id
                    and not line.tax_line_id
                )
            )
        return lines

    def _l10n_ar_rg5329_base_by_rate(self):
        self.ensure_one()
        company = self.company_id
        perception_taxes = company._l10n_ar_rg5329_perception_taxes()
        reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()

        bases = {rate_key: 0.0 for rate_key in RG5329_TAX_SPECS}

        for line in self._l10n_ar_rg5329_invoice_product_lines():
            taxes_without_rg = line.tax_ids - perception_taxes

            if line.product_id.categ_id.id not in reached_category_ids:
                continue

            rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(taxes_without_rg)

            if rate_key:
                bases[rate_key] += line.price_subtotal

        _logger.info("RG5329 MOVE BASES ACUMULADAS: %s", bases)
        return bases

    def _l10n_ar_rg5329_applicable_rate_keys(self):
        self.ensure_one()

        if not self._l10n_ar_rg5329_can_apply():
            return set()

        invoice_currency = self.currency_id or self.company_currency_id
        company_currency = self.company_id.currency_id
        conversion_date = self.invoice_date or fields.Date.context_today(self)

        applicable = set()
        bases = self._l10n_ar_rg5329_base_by_rate()

        for rate_key, base in bases.items():
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

            _logger.info(
                "RG5329 MOVE RATE CHECK rate_key=%s base_total=%s alicuota=%s perception=%s min=%s",
                rate_key,
                base,
                RG5329_TAX_SPECS[rate_key]["amount"],
                perception_amount_company,
                self.company_id.l10n_ar_rg5329_min_amount,
            )

            if (
                float_compare(
                    perception_amount_company,
                    self.company_id.l10n_ar_rg5329_min_amount,
                    precision_rounding=company_currency.rounding,
                )
                >= 0
            ):
                applicable.add(rate_key)

        _logger.info("RG5329 MOVE RATE KEYS APLICABLES: %s", applicable)
        return applicable

    def _l10n_ar_rg5329_sync_invoice_taxes(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue

            company = move.company_id

            if company.l10n_ar_rg5329_enabled:
                company._l10n_ar_rg5329_ensure_taxes()

            perception_taxes = company._l10n_ar_rg5329_perception_taxes()
            tax_by_rate = company._l10n_ar_rg5329_perception_tax_by_rate()
            reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()
            product_lines = move._l10n_ar_rg5329_invoice_product_lines()

            _logger.info("========== RG5329 MOVE ==========")
            _logger.info("Factura: %s", move.name or "Nueva")
            _logger.info("Estado: %s", move.state)
            _logger.info("Cliente: %s", move.partner_id.display_name)
            _logger.info("Regimen habilitado: %s", company.l10n_ar_rg5329_enabled)
            _logger.info(
                "Cliente alcanzado: %s",
                company._l10n_ar_rg5329_is_partner_reached(move.partner_id),
            )
            _logger.info("Cantidad lineas producto: %s", len(product_lines))

            if not product_lines:
                _logger.info(
                    "RG5329 MOVE >>> Sin lineas visibles. No recalculo para no pisar onchange."
                )
                continue

            applicable_rate_keys = move._l10n_ar_rg5329_applicable_rate_keys()

            for line in product_lines:
                taxes = line.tax_ids - perception_taxes
                rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(taxes)

                should_apply = (
                    move._l10n_ar_rg5329_can_apply()
                    and line.product_id
                    and line.product_id.categ_id.id in reached_category_ids
                    and rate_key in applicable_rate_keys
                )

                _logger.info(
                    "RG5329 MOVE LINE product=%s subtotal=%s rate=%s should_apply=%s taxes=%s",
                    line.product_id.display_name,
                    line.price_subtotal,
                    rate_key,
                    should_apply,
                    taxes.mapped("name"),
                )

                if should_apply:
                    perception_tax = tax_by_rate.get(rate_key)
                    if perception_tax:
                        _logger.info("RG5329 MOVE >>> AGREGO %s", perception_tax.name)
                        taxes |= perception_tax

                if set(taxes.ids) != set(line.tax_ids.ids):
                    line.with_context(
                        l10n_ar_rg5329_skip_invoice_sync=True
                    ).tax_ids = taxes


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.onchange(
        "product_id",
        "quantity",
        "price_unit",
        "discount",
        "tax_ids",
    )
    def _onchange_l10n_ar_rg5329_line_fields(self):
        for line in self:
            move = line.move_id

            if not move or move.move_type != "out_invoice":
                continue

            company = move.company_id

            if company.l10n_ar_rg5329_enabled:
                company._l10n_ar_rg5329_ensure_taxes()

            perception_taxes = company._l10n_ar_rg5329_perception_taxes()
            tax_by_rate = company._l10n_ar_rg5329_perception_tax_by_rate()
            reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()

            taxes = line.tax_ids - perception_taxes

            _logger.info("========== RG5329 LINE ==========")
            _logger.info("Producto: %s", line.product_id.display_name)
            _logger.info("Cliente: %s", move.partner_id.display_name)
            _logger.info("Regimen habilitado: %s", company.l10n_ar_rg5329_enabled)
            _logger.info(
                "Cliente alcanzado: %s",
                company._l10n_ar_rg5329_is_partner_reached(move.partner_id),
            )
            _logger.info("Subtotal linea: %s", line.price_subtotal)
            _logger.info("Impuestos sin RG: %s", taxes.mapped("name"))

            if not (
                move.state == "draft"
                and company.l10n_ar_rg5329_enabled
                and company._l10n_ar_rg5329_is_partner_reached(move.partner_id)
                and line.product_id
                and line.product_id.categ_id.id in reached_category_ids
            ):
                _logger.info("RG5329 LINE >>> NO APLICA POR CONDICIONES BASE")
                line.tax_ids = taxes
                continue

            current_rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(taxes)
            _logger.info("IVA detectado linea actual: %s", current_rate_key)

            if not current_rate_key:
                _logger.info("RG5329 LINE >>> NO APLICA, NO DETECTA IVA")
                line.tax_ids = taxes
                continue

            base = line.price_subtotal
            perception_amount = (
                base * RG5329_TAX_SPECS[current_rate_key]["amount"] / 100.0
            )

            _logger.info(
                "RG5329 LINE RATE CHECK rate_key=%s base_linea=%s alicuota=%s perception=%s min=%s",
                current_rate_key,
                base,
                RG5329_TAX_SPECS[current_rate_key]["amount"],
                perception_amount,
                company.l10n_ar_rg5329_min_amount,
            )

            if (
                float_compare(
                    perception_amount,
                    company.l10n_ar_rg5329_min_amount,
                    precision_rounding=move.currency_id.rounding,
                )
                >= 0
            ):
                perception_tax = tax_by_rate.get(current_rate_key)
                if perception_tax:
                    _logger.info("RG5329 LINE >>> AGREGO %s", perception_tax.name)
                    line.tax_ids = taxes | perception_tax
                else:
                    line.tax_ids = taxes
            else:
                _logger.info("RG5329 LINE >>> NO APLICA POR MINIMO")
                line.tax_ids = taxes
