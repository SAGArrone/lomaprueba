from odoo import _, fields, models
from odoo.exceptions import ValidationError


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

    def set_values(self):
        res = super().set_values()
        company = self.company_id.sudo()

        if company.l10n_ar_rg5329_enabled:
            if not company.l10n_ar_rg5329_account_id:
                raise ValidationError(
                    _("Debe configurar la cuenta contable de percepcion RG 5329.")
                )
            if not company.l10n_ar_rg5329_tax_group_id:
                raise ValidationError(
                    _("Debe configurar el grupo de impuestos RG 5329.")
                )

            company._l10n_ar_rg5329_apply_configuration()

        return res