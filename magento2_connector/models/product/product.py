from odoo import models, fields
from odoo.addons import decimal_precision as dp


class ProductProduct(models.Model):
    _inherit = 'product.product'

    magento_bind_ids = fields.One2many(
        'magento.product.product',
        'odoo_id',
        string='Magento Bindings Product',
    )
    magento_product_name = fields.Char('Magento Product Name', index=True, translate=True)
    is_magento_product = fields.Boolean("Is Magento Product")

    magento_sale_price = fields.Float(
        'Magento Sale Price',
        digits=dp.get_precision('Product Price'),
        help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.")
