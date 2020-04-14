from odoo import fields, _, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        string='Magento Backend',
        ondelete='restrict',
    )
    external_id = fields.Integer(string='ID on Magento')

    magento_bind_ids = fields.One2many(
        'magento.product.attribute',
        'odoo_id',
        string='Magento Bindings',
    )


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    magento_value = fields.Char(_("Magento Value"))
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        string='Magento Backend',
        ondelete='restrict',
    )
    attribute_id_external_id = fields.Integer(string='Attribute ID on Magento')
