import logging

from odoo import api, fields, models
from odoo.tools import float_compare

from .res_company import RG5329_TAX_SPECS


_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange(
        "invoice_line_ids",
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

            _logger.info(
                "RG5329 base/rate: rate_key=%s base=%s perception=%s perception_company=%s min=%s",
                rate_key,
                base,
                perception_amount,
                perception_amount_company,
                self.company_id.l10n_ar_rg5329_min_amount,
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

            _logger.info("========== RG5329 ==========")
            _logger.info("Factura: %s", move.name or "Nueva")
            _logger.info("Estado: %s", move.state)
            _logger.info("Tipo: %s", move.move_type)
            _logger.info("Cliente: %s", move.partner_id.display_name)
            _logger.info("Empresa: %s", company.display_name)
            _logger.info("Regimen habilitado: %s", company.l10n_ar_rg5329_enabled)
            _logger.info(
                "Responsabilidad cliente: %s",
                move.partner_id.commercial_partner_id.l10n_ar_afip_responsibility_type_id.display_name,
            )
            _logger.info(
                "Cliente alcanzado: %s",
                company._l10n_ar_rg5329_is_partner_reached(move.partner_id),
            )
            _logger.info(
                "Categorias configuradas: %s",
                company.l10n_ar_rg5329_product_categ_ids.mapped("display_name"),
            )
            _logger.info(
                "Categorias alcanzadas IDs: %s",
                company._l10n_ar_rg5329_reached_category_ids(),
            )
            _logger.info("Minimo percepcion: %s", company.l10n_ar_rg5329_min_amount)

            perception_taxes = company._l10n_ar_rg5329_perception_taxes()

            if company.l10n_ar_rg5329_enabled:
                company._l10n_ar_rg5329_ensure_taxes()
                perception_taxes = company._l10n_ar_rg5329_perception_taxes()

            tax_by_rate = company._l10n_ar_rg5329_perception_tax_by_rate()
            reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()
            applicable_rate_keys = move._l10n_ar_rg5329_applicable_rate_keys()

            _logger.info(
                "Impuestos RG encontrados: %s",
                perception_taxes.mapped("name"),
            )
            _logger.info(
                "Tax by rate: %s",
                {k: v.mapped("name") for k, v in tax_by_rate.items()},
            )
            _logger.info("Rate keys aplicables: %s", applicable_rate_keys)

            for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                taxes = line.tax_ids - perception_taxes
                rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(taxes)

                _logger.info("--------------------------------")
                _logger.info("Producto: %s", line.product_id.display_name)
                _logger.info(
                    "Categoria: %s (%s)",
                    line.product_id.categ_id.display_name,
                    line.product_id.categ_id.id,
                )
                _logger.info("Subtotal: %s", line.price_subtotal)
                _logger.info("Impuestos originales: %s", line.tax_ids.mapped("name"))
                _logger.info("Impuestos sin RG: %s", taxes.mapped("name"))
                _logger.info("IVA detectado: %s", rate_key)
                _logger.info(
                    "Categoria incluida: %s",
                    line.product_id.categ_id.id in reached_category_ids,
                )

                should_apply = (
                    move._l10n_ar_rg5329_can_apply()
                    and line.product_id
                    and line.product_id.categ_id.id in reached_category_ids
                )

                _logger.info("Debe aplicar por condiciones base: %s", should_apply)

                if should_apply:
                    perception_tax = tax_by_rate.get(rate_key)
                    _logger.info(
                        "Impuesto percepcion para rate_key: %s",
                        perception_tax.mapped("name") if perception_tax else "NINGUNO",
                    )

                    if rate_key in applicable_rate_keys and perception_tax:
                        _logger.info(">>> AGREGO PERCEPCION RG5329 <<<")
                        taxes |= perception_tax
                    else:
                        _logger.info(">>> NO AGREGO PERCEPCION RG5329 <<<")

                _logger.info("Impuestos finales: %s", taxes.mapped("name"))

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
            if line.move_id:
                line.move_id._l10n_ar_rg5329_sync_invoice_taxes()
