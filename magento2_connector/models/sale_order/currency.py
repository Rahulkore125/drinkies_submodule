from odoo import fields, models


class ProductPriceList(models.Model):
    _inherit = 'product.pricelist'

    backend_id = fields.Integer()

    _sql_constraints = [
        ('uniq_name_and_magento_backend', 'unique(name,backend_id)', "The name_and_magento_backend must be unique !")]


class Currency(models.Model):
    _inherit = "res.currency"

    product_price_list_ids = fields.One2many("product.pricelist", 'currency_id')
