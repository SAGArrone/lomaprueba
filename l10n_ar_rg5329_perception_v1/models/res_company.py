from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


RG5329_TAX_SPECS = {
    "vat_21": {
        "name": "Percepcion IVA RG 5329/2023 3%",
        "amount": 3.0,
        "vat_amount": 21.0,
    },
    "vat_10_5": {
        "name": "Percepcion IVA RG 5329/2023 1,5%",
        "amount": 1.5,
        "vat_amount": 10.5,
    },
}


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_ar_rg5329_enabled = fields.Boolean(
        string="Habilitar regimen RG 5329/2023",
    )
    l10n_ar_rg5329_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta percepcion RG 5329",
        domain="[('deprecated', '=', False)]",
        check_company=True,
    )
    l10n_ar_rg5329_tax_group_id = fields.Many2one(
        comodel_name="account.tax.group",
        string="Grupo de impuestos RG 5329",
    )
    l10n_ar_rg5329_min_amount = fields.Monetary(
        string="Importe minimo de percepcion",
        currency_field="currency_id",
        default=3000.0,
    )
    l10n_ar_rg5329_responsibility_type_ids = fields.Many2many(
        comodel_name="l10n_ar.afip.responsibility.type",
        relation="l10n_ar_rg5329_company_responsibility_rel",
        column1="company_id",
        column2="responsibility_type_id",
        string="Tipos de contribuyentes alcanzados",
        default=lambda self: self._l10n_ar_rg5329_default_responsibility_types(),
    )
    l10n_ar_rg5329_product_categ_ids = fields.Many2many(
        comodel_name="product.category",
        relation="l10n_ar_rg5329_company_product_categ_rel",
        column1="company_id",
        column2="category_id",
        string="Categorias de productos alcanzadas",
    )

    @api.model
    def _l10n_ar_rg5329_default_responsibility_types(self):
        return self.env["l10n_ar.afip.responsibility.type"].search(
            [("name", "ilike", "Responsable Inscripto")],
            limit=1,
        )

    @api.constrains("l10n_ar_rg5329_min_amount")
    def _check_l10n_ar_rg5329_min_amount(self):
        for company in self:
            if company.l10n_ar_rg5329_min_amount < 0:
                raise ValidationError(
                    _("El importe minimo de percepcion no puede ser negativo.")
                )

    def _l10n_ar_rg5329_has_required_configuration(self):
        self.ensure_one()
        return bool(
            self.l10n_ar_rg5329_enabled
            and self.l10n_ar_rg5329_account_id
            and self.l10n_ar_rg5329_tax_group_id
        )

    def write(self, vals):
        res = super().write(vals)
        watched_fields = {
            "l10n_ar_rg5329_enabled",
            "l10n_ar_rg5329_account_id",
            "l10n_ar_rg5329_tax_group_id",
            "l10n_ar_rg5329_min_amount",
            "l10n_ar_rg5329_responsibility_type_ids",
            "l10n_ar_rg5329_product_categ_ids",
        }
        if (
            watched_fields.intersection(vals)
            and not self.env.context.get("l10n_ar_rg5329_skip_apply")
        ):
            self._l10n_ar_rg5329_apply_configuration()
        return res

    def action_l10n_ar_rg5329_sync_products(self):
        for company in self:
            if not company._l10n_ar_rg5329_has_required_configuration():
                raise ValidationError(
                    _(
                        "Debe habilitar el regimen RG 5329 y configurar cuenta contable "
                        "y grupo de impuestos antes de actualizar productos."
                    )
                )
            company._l10n_ar_rg5329_ensure_taxes()
            company._l10n_ar_rg5329_sync_products()
            company._l10n_ar_rg5329_sync_draft_invoices()
        return True

    def _l10n_ar_rg5329_apply_configuration(self):
        for company in self:
            if company._l10n_ar_rg5329_has_required_configuration():
                company._l10n_ar_rg5329_ensure_taxes()
            company._l10n_ar_rg5329_sync_products()
            company._l10n_ar_rg5329_sync_draft_invoices()

    def _l10n_ar_rg5329_tax_values(self, rate_key):
        self.ensure_one()
        spec = RG5329_TAX_SPECS[rate_key]
        return {
            "name": spec["name"],
            "amount_type": "percent",
            "amount": spec["amount"],
            "type_tax_use": "sale",
            "company_id": self.id,
            "tax_group_id": self.l10n_ar_rg5329_tax_group_id.id,
            "price_include": False,
            "include_base_amount": False,
            "l10n_ar_rg5329_perception": True,
            "l10n_ar_rg5329_vat_rate": rate_key,
            "invoice_repartition_line_ids": [
                Command.create({"repartition_type": "base", "factor_percent": 100.0}),
                Command.create({
                    "repartition_type": "tax",
                    "factor_percent": 100.0,
                    "account_id": self.l10n_ar_rg5329_account_id.id,
                }),
            ],
            "refund_repartition_line_ids": [
                Command.create({"repartition_type": "base", "factor_percent": 100.0}),
                Command.create({
                    "repartition_type": "tax",
                    "factor_percent": 100.0,
                    "account_id": self.l10n_ar_rg5329_account_id.id,
                }),
            ],
        }

    def _l10n_ar_rg5329_find_tax(self, rate_key):
        self.ensure_one()
        return self.env["account.tax"].sudo().with_company(self).search(
            [
                ("company_id", "=", self.id),
                ("l10n_ar_rg5329_perception", "=", True),
                ("l10n_ar_rg5329_vat_rate", "=", rate_key),
                ("type_tax_use", "=", "sale"),
                ("active", "in", [True, False]),
            ],
            limit=1,
        )

    def _l10n_ar_rg5329_ensure_taxes(self):
        MoveLine = self.env["account.move.line"].sudo()
        Tax = self.env["account.tax"].sudo()
        for company in self:
            if not company._l10n_ar_rg5329_has_required_configuration():
                continue
            for rate_key, spec in RG5329_TAX_SPECS.items():
                tax = company._l10n_ar_rg5329_find_tax(rate_key)
                if not tax:
                    Tax.with_company(company).create(company._l10n_ar_rg5329_tax_values(rate_key))
                    continue

                # Safe metadata update only. Do not change computation on taxes already used.
                tax.write({
                    "active": True,
                    "l10n_ar_rg5329_perception": True,
                    "l10n_ar_rg5329_vat_rate": rate_key,
                })
                move_line_count = MoveLine.search_count([
                    "|",
                    ("tax_line_id", "=", tax.id),
                    ("tax_ids", "in", tax.id),
                ])
                if move_line_count:
                    continue

                tax.write({
                    "name": spec["name"],
                    "amount_type": "percent",
                    "amount": spec["amount"],
                    "type_tax_use": "sale",
                    "tax_group_id": company.l10n_ar_rg5329_tax_group_id.id,
                    "price_include": False,
                    "include_base_amount": False,
                    "l10n_ar_rg5329_perception": True,
                    "l10n_ar_rg5329_vat_rate": rate_key,
                })
                tax.invoice_repartition_line_ids.filtered(
                    lambda line: line.repartition_type == "tax"
                ).write({"account_id": company.l10n_ar_rg5329_account_id.id})
                tax.refund_repartition_line_ids.filtered(
                    lambda line: line.repartition_type == "tax"
                ).write({"account_id": company.l10n_ar_rg5329_account_id.id})

    def _l10n_ar_rg5329_perception_taxes(self):
        self.ensure_one()
        return self.env["account.tax"].sudo().with_company(self).search(
            [
                ("company_id", "=", self.id),
                ("l10n_ar_rg5329_perception", "=", True),
                ("active", "=", True),
            ]
        )

    def _l10n_ar_rg5329_perception_tax_by_rate(self):
        self.ensure_one()
        taxes = self._l10n_ar_rg5329_perception_taxes()
        return {
            rate_key: taxes.filtered(
                lambda tax, key=rate_key: tax.l10n_ar_rg5329_vat_rate == key
            )[:1]
            for rate_key in RG5329_TAX_SPECS
        }

    def _l10n_ar_rg5329_reached_category_ids(self):
        self.ensure_one()
        categories = self.l10n_ar_rg5329_product_categ_ids
        if not categories:
            return set(self.env["product.category"].sudo().search([]).ids)
        reached_categories = self.env["product.category"].sudo().search(
            [("id", "child_of", categories.ids)]
        )
        return set(reached_categories.ids)

    def _l10n_ar_rg5329_is_partner_reached(self, partner):
        self.ensure_one()
        if not partner or not self.l10n_ar_rg5329_responsibility_type_ids:
            return False
        partner = partner.commercial_partner_id or partner
        responsibility = partner.l10n_ar_afip_responsibility_type_id
        return bool(
            responsibility
            and responsibility in self.l10n_ar_rg5329_responsibility_type_ids
        )

    def _l10n_ar_rg5329_rate_key_from_taxes(self, taxes):
        taxes = taxes.filtered(lambda tax: not tax.l10n_ar_rg5329_perception)
        for rate_key, spec in RG5329_TAX_SPECS.items():
            matched = taxes.filtered(
                lambda tax, amount=spec["vat_amount"]: tax.amount_type == "percent"
                and tax.type_tax_use in ("sale", "none")
                and float_compare(tax.amount, amount, precision_digits=2) == 0
            )
            if matched:
                return rate_key
        return False

    def _l10n_ar_rg5329_base_taxes(self, taxes):
        self.ensure_one()
        return taxes - self._l10n_ar_rg5329_perception_taxes()

    def _l10n_ar_rg5329_sync_products(self):
        ProductTemplate = self.env["product.template"].sudo()
        for company in self:
            templates = ProductTemplate.with_company(company).search([])
            templates._l10n_ar_rg5329_sync_perception_taxes(company)

    def _l10n_ar_rg5329_sync_draft_invoices(self):
        Move = self.env["account.move"].sudo()
        for company in self:
            moves = Move.with_company(company).search([
                ("company_id", "=", company.id),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "draft"),
            ])
            moves._l10n_ar_rg5329_sync_invoice_taxes()
