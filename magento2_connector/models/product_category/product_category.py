from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = 'product.category'

    magento_bind_ids = fields.One2many(
        'magento.product.category',
        'odoo_id',
        string="Magento Bindings",
    )
