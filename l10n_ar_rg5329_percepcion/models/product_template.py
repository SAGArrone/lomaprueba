from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # RG 5329 no se asigna en productos.
    # Se calcula dinamicamente en facturas por cliente, documento, categoria y acumulado por alicuota.
    pass
