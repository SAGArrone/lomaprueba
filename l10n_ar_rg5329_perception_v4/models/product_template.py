from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # Intentionally no automatic RG5329 tax assignment on products.
    # RG5329 depends on partner responsibility and invoice amount, so it must be
    # applied dynamically on invoices only.
    pass
