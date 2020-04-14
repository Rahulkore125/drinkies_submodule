from odoo import models, fields


class MagentoProductAttribute(models.Model):
    _name = 'magento.product.attribute'
    _inherits = {'product.attribute': 'odoo_id'}
    _inherit = 'magento.binding'
    _description = 'Magento Product Attribute'

    odoo_id = fields.Many2one('product.attribute', required=True, ondelete="cascade")
