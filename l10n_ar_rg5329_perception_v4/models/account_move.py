import logging

from odoo import api, fields, models
from odoo.tools import float_compare

from .res_company import RG5329_TAX_SPECS


_logger = logging.getLogger(__name__)


RG5329_LEGAL_INVOICE_DOCUMENT_CODES = {
    "1", "6", "11", "19", "20", "21", "51", "201", "206", "211",
}


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        if not self.env.context.get("l10n_ar_rg5329_skip_invoice_sync"):
            moves._l10n_ar_rg5329_sync_invoice_taxes()
        return moves

    def write(self, vals):
        res = super().write(vals)
        watched_fields = {
            "invoice_line_ids",
            "partner_id",
            "move_type",
            "company_id",
            "fiscal_position_id",
            "journal_id",
            "l10n_latam_document_type_id",
            "invoice_date",
            "currency_id",
        }
        if watched_fields.intersection(vals) and not self.env.context.get("l10n_ar_rg5329_skip_invoice_sync"):
            self._l10n_ar_rg5329_sync_invoice_taxes()
        return res

    @api.onchange(
        "invoice_line_ids",
        "partner_id",
        "move_type",
        "company_id",
        "fiscal_position_id",
        "journal_id",
        "l10n_latam_document_type_id",
        "invoice_date",
        "currency_id",
    )
    def _onchange_l10n_ar_rg5329_sync_invoice_taxes(self):
        self._l10n_ar_rg5329_sync_invoice_taxes()

    def action_post(self):
        self._l10n_ar_rg5329_sync_invoice_taxes()
        return super().action_post()

    def _l10n_ar_rg5329_has_legal_document(self):
        self.ensure_one()
        journal = self.journal_id
        document_type = self.l10n_latam_document_type_id

        if self.company_id.account_fiscal_country_id.code != "AR":
            return False

        if not (
            journal
            and journal.type == "sale"
            and getattr(journal, "l10n_latam_use_documents", False)
            and getattr(journal, "l10n_ar_is_pos", False)
            and document_type
        ):
            return False

        internal_type = getattr(document_type, "internal_type", False)
        if internal_type:
            return internal_type == "invoice"

        return str(document_type.code) in RG5329_LEGAL_INVOICE_DOCUMENT_CODES

    def _l10n_ar_rg5329_can_apply(self):
        self.ensure_one()
        company = self.company_id

        return (
            (self.state or "draft") == "draft"
            and self.move_type == "out_invoice"
            and company.l10n_ar_rg5329_enabled
            and company._l10n_ar_rg5329_has_required_configuration()
            and company._l10n_ar_rg5329_is_partner_reached(self.partner_id)
            and self._l10n_ar_rg5329_has_legal_document()
        )

    def _l10n_ar_rg5329_clean_taxes(self, taxes):
        return taxes.filtered(
            lambda tax: not tax.l10n_ar_rg5329_perception
            and "RG 5329" not in (tax.name or "")
        )

    def _l10n_ar_rg5329_invoice_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: not line.display_type and not line.tax_line_id
        )

    def _l10n_ar_rg5329_line_base_amount(self, line):
        if line.quantity and line.price_unit:
            return line.quantity * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
        return line.price_subtotal or 0.0

    def _l10n_ar_rg5329_line_is_reached(self, line, reached_category_ids):
        product = line.product_id
        if not product:
            return False
        return product.categ_id.id in reached_category_ids

    def _l10n_ar_rg5329_lines_by_rate(self):
        self.ensure_one()
        company = self.company_id
        reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()

        result = {
            rate_key: {
                "base": 0.0,
                "lines": self.env["account.move.line"],
            }
            for rate_key in RG5329_TAX_SPECS
        }

        for line in self._l10n_ar_rg5329_invoice_lines():
            clean_taxes = self._l10n_ar_rg5329_clean_taxes(line.tax_ids)

            if not self._l10n_ar_rg5329_line_is_reached(line, reached_category_ids):
                continue

            rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(clean_taxes)
            if not rate_key:
                continue

            result[rate_key]["base"] += self._l10n_ar_rg5329_line_base_amount(line)
            result[rate_key]["lines"] |= line

        return result

    def _l10n_ar_rg5329_applicable_rate_keys(self, lines_by_rate):
        self.ensure_one()

        invoice_currency = self.currency_id or self.company_currency_id
        company_currency = self.company_id.currency_id
        conversion_date = self.invoice_date or fields.Date.context_today(self)

        applicable = set()

        for rate_key, data in lines_by_rate.items():
            base = data["base"]

            if not base:
                continue

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
                "RG5329 CHECK rate=%s base_acumulada=%s percepcion=%s minimo=%s",
                rate_key,
                base,
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

        return applicable

    def _l10n_ar_rg5329_sync_invoice_taxes(self):
        for move in self:
            if move.move_type != "out_invoice" or (move.state or "draft") != "draft":
                continue

            company = move.company_id

            if company.l10n_ar_rg5329_enabled:
                company._l10n_ar_rg5329_ensure_taxes()

            tax_by_rate = company._l10n_ar_rg5329_perception_tax_by_rate()
            invoice_lines = move._l10n_ar_rg5329_invoice_lines()

            if not invoice_lines:
                continue

            if not move._l10n_ar_rg5329_can_apply():
                for line in invoice_lines:
                    clean_taxes = move._l10n_ar_rg5329_clean_taxes(line.tax_ids)
                    if set(clean_taxes.ids) != set(line.tax_ids.ids):
                        line.with_context(l10n_ar_rg5329_skip_invoice_sync=True).tax_ids = clean_taxes
                continue

            lines_by_rate = move._l10n_ar_rg5329_lines_by_rate()
            applicable_rate_keys = move._l10n_ar_rg5329_applicable_rate_keys(lines_by_rate)

            _logger.info("RG5329 ALICUOTAS APLICABLES: %s", applicable_rate_keys)

            for rate_key, data in lines_by_rate.items():
                perception_tax = tax_by_rate.get(rate_key)
                affected_lines = data["lines"]

                for line in affected_lines:
                    taxes = move._l10n_ar_rg5329_clean_taxes(line.tax_ids)

                    if rate_key in applicable_rate_keys and perception_tax:
                        taxes |= perception_tax

                    if set(taxes.ids) != set(line.tax_ids.ids):
                        line.with_context(l10n_ar_rg5329_skip_invoice_sync=True).tax_ids = taxes

            reached_lines = self.env["account.move.line"]
            for data in lines_by_rate.values():
                reached_lines |= data["lines"]

            not_reached_lines = invoice_lines - reached_lines
            for line in not_reached_lines:
                clean_taxes = move._l10n_ar_rg5329_clean_taxes(line.tax_ids)
                if set(clean_taxes.ids) != set(line.tax_ids.ids):
                    line.with_context(l10n_ar_rg5329_skip_invoice_sync=True).tax_ids = clean_taxes

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
            if (
                move
                and move.move_type == "out_invoice"
                and (move.state or "draft") == "draft"
                and not self.env.context.get("l10n_ar_rg5329_skip_invoice_sync")
            ):
                move._l10n_ar_rg5329_sync_invoice_taxes()
