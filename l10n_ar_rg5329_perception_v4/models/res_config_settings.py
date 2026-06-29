from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_ar_rg5329_enabled = fields.Boolean(
        related="company_id.l10n_ar_rg5329_enabled",
        readonly=False,
    )
    l10n_ar_rg5329_account_id = fields.Many2one(
        related="company_id.l10n_ar_rg5329_account_id",
        readonly=False,
    )
    l10n_ar_rg5329_tax_group_id = fields.Many2one(
        related="company_id.l10n_ar_rg5329_tax_group_id",
        readonly=False,
    )
    l10n_ar_rg5329_min_amount = fields.Monetary(
        related="company_id.l10n_ar_rg5329_min_amount",
        readonly=False,
    )
    l10n_ar_rg5329_responsibility_type_ids = fields.Many2many(
        related="company_id.l10n_ar_rg5329_responsibility_type_ids",
        readonly=False,
    )
    l10n_ar_rg5329_product_categ_ids = fields.Many2many(
        related="company_id.l10n_ar_rg5329_product_categ_ids",
        readonly=False,
    )

    def action_l10n_ar_rg5329_sync_products(self):
        self.ensure_one()
        return self.company_id.action_l10n_ar_rg5329_sync_products()
