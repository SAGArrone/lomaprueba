import logging

from odoo import api, fields, models
from odoo.tools import float_compare

from .res_company import RG5329_TAX_SPECS


_logger = logging.getLogger(__name__)


RG5329_LEGAL_INVOICE_DOCUMENT_CODES = {
    "1",
    "6",
    "11",
    "19",
    "20",
    "21",
    "51",
    "201",
    "206",
    "211",
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
        if watched_fields.intersection(vals) and not self.env.context.get(
            "l10n_ar_rg5329_skip_invoice_sync"
        ):
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
        return bool(
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

    def _l10n_ar_rg5329_invoice_base_lines(self):
        self.ensure_one()

        candidate_lines = self.invoice_line_ids | self.line_ids

        def _is_base_line(line):
            if line.display_type in ("line_section", "line_note"):
                return False

            if line.display_type in ("tax", "payment_term", "rounding", "cogs"):
                return False

            if line.tax_line_id:
                return False

            account_type = getattr(line.account_id, "account_type", False)
            if account_type in ("asset_receivable", "liability_payable"):
                return False

            return bool(
                line.product_id
                or line.tax_ids
                or line.quantity
                or line.price_unit
                or line.price_subtotal
                or line.name
            )

        lines = candidate_lines.filtered(_is_base_line)

        _logger.info("===== DEBUG RG5329 LINEAS =====")
        _logger.info(
            "RG5329 V5.2 LINEAS DETECTADAS invoice_line_ids=%s line_ids=%s base=%s display_types=%s",
            len(self.invoice_line_ids),
            len(self.line_ids),
            len(lines),
            candidate_lines.mapped("display_type"),
        )

        for line in candidate_lines:
            _logger.info(
                "RG5329 LINE id=%s display=%s product=%s tax_line=%s account_type=%s subtotal=%s price_unit=%s qty=%s taxes=%s",
                line.id,
                line.display_type,
                line.product_id.display_name if line.product_id else None,
                bool(line.tax_line_id),
                getattr(line.account_id, "account_type", False),
                line.price_subtotal,
                line.price_unit,
                line.quantity,
                line.tax_ids.mapped("name"),
            )

        return lines
    
    def _l10n_ar_rg5329_line_base_amount(self, line):
        if line.quantity and line.price_unit:
            return line.quantity * line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
        return line.price_subtotal or 0.0

    def _l10n_ar_rg5329_line_is_reached(self, line, reached_category_ids):
        product = line.product_id
        if not product:
            return False
        return product.categ_id.id in reached_category_ids

    def _l10n_ar_rg5329_collect_by_rate(self, lines=None):
        self.ensure_one()
        company = self.company_id
        reached_category_ids = company._l10n_ar_rg5329_reached_category_ids()
        lines = lines if lines is not None else self._l10n_ar_rg5329_invoice_base_lines()

        result = {
            rate_key: {
                "base": 0.0,
                "lines": self.env["account.move.line"],
            }
            for rate_key in RG5329_TAX_SPECS
        }

        for line in lines:
            clean_taxes = self._l10n_ar_rg5329_clean_taxes(line.tax_ids)
            if not self._l10n_ar_rg5329_line_is_reached(line, reached_category_ids):
                continue
            rate_key = company._l10n_ar_rg5329_rate_key_from_taxes(clean_taxes)
            if not rate_key:
                continue
            result[rate_key]["base"] += self._l10n_ar_rg5329_line_base_amount(line)
            result[rate_key]["lines"] |= line

        _logger.info(
            "RG5329 V5.2 BASES ACUMULADAS POR ALICUOTA: %s",
            {key: value["base"] for key, value in result.items()},
        )
        return result

    def _l10n_ar_rg5329_applicable_rate_keys(self, grouped_lines):
        self.ensure_one()
        invoice_currency = self.currency_id or self.company_currency_id
        company_currency = self.company_id.currency_id
        conversion_date = self.invoice_date or fields.Date.context_today(self)
        applicable = set()

        for rate_key, data in grouped_lines.items():
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
                "RG5329 V5.2 CHECK rate=%s base_acumulada=%s percepcion_moneda_compania=%s minimo=%s",
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

        _logger.info("RG5329 V5.2 ALICUOTAS APLICABLES: %s", applicable)
        return applicable

    def _l10n_ar_rg5329_sync_invoice_taxes(self):
        for move in self:
            if move.move_type != "out_invoice" or (move.state or "draft") != "draft":
                continue
            if move.env.context.get("l10n_ar_rg5329_skip_invoice_sync"):
                continue

            company = move.company_id
            if company.l10n_ar_rg5329_enabled:
                company._l10n_ar_rg5329_ensure_taxes()

            lines = move._l10n_ar_rg5329_invoice_base_lines()
            if not lines:
                _logger.info("RG5329 V5.2: factura sin lineas base para evaluar")
                continue

            if not move._l10n_ar_rg5329_can_apply():
                _logger.info("RG5329 V5.2: condiciones generales no alcanzadas, limpio percepciones")
                for line in lines:
                    clean_taxes = move._l10n_ar_rg5329_clean_taxes(line.tax_ids)
                    if set(clean_taxes.ids) != set(line.tax_ids.ids):
                        line.with_context(l10n_ar_rg5329_skip_invoice_sync=True).tax_ids = clean_taxes
                continue

            tax_by_rate = company._l10n_ar_rg5329_perception_tax_by_rate()
            grouped_lines = move._l10n_ar_rg5329_collect_by_rate(lines=lines)
            applicable_rate_keys = move._l10n_ar_rg5329_applicable_rate_keys(grouped_lines)

            reached_lines = self.env["account.move.line"]
            for rate_key, data in grouped_lines.items():
                reached_lines |= data["lines"]
                perception_tax = tax_by_rate.get(rate_key)
                for line in data["lines"]:
                    taxes = move._l10n_ar_rg5329_clean_taxes(line.tax_ids)
                    if rate_key in applicable_rate_keys and perception_tax:
                        taxes |= perception_tax
                    if set(taxes.ids) != set(line.tax_ids.ids):
                        line.with_context(l10n_ar_rg5329_skip_invoice_sync=True).tax_ids = taxes

            # Las lineas no alcanzadas o sin IVA 21/10,5 deben quedar sin percepcion RG 5329.
            not_reached_lines = lines - reached_lines
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
        # Este onchange no decide por linea. Solo fuerza el recalculo centralizado del account.move.
        if self.env.context.get("l10n_ar_rg5329_skip_invoice_sync"):
            return
        moves = self.mapped("move_id").filtered(
            lambda move: move.move_type == "out_invoice"
            and (move.state or "draft") == "draft"
        )
        moves._l10n_ar_rg5329_sync_invoice_taxes()
