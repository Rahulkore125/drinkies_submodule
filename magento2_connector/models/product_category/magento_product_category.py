from odoo import models, fields


class MagentoProductCategory(models.Model):
    _name = 'magento.product.category'
    _inherit = 'magento.binding'
    _inherits = {'product.category': 'odoo_id'}
    _description = 'Magento Product Category'

    odoo_id = fields.Many2one('product.category',
                              string='Product Category',
                              required=True,
                              ondelete='cascade')
    description = fields.Text(translate=True)
    name = fields.Char("Name")
    magento_parent_id = fields.Many2one(
        'magento.product.category',
        'Magento Parent Category',
        ondelete='cascade',
    )
    magento_child_ids = fields.One2many(
        'magento.product.category',
        'magento_parent_id',
        string='Magento Child Categories',
    )
    product_count = fields.Integer("Product amount")
