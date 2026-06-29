from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ar_rg5329_perception = fields.Boolean(
        string="Percepcion IVA RG 5329/2023",
        copy=False,
        index=True,
    )
    l10n_ar_rg5329_vat_rate = fields.Selection(
        selection=[
            ("vat_21", "IVA 21%"),
            ("vat_10_5", "IVA 10,5%"),
        ],
        string="Alicuota IVA RG 5329",
        copy=False,
        index=True,
    )

