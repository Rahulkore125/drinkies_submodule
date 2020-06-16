from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_discount_product = fields.Boolean(string="Is Discount Product", default=False)
