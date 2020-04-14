from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    magento_bind_ids = fields.One2many(
        'magento.res.partner',
        'odoo_id',
        string="Magento Bindings",
    )
    magento_address_bind_ids = fields.One2many(
        'magento.address',
        'odoo_id',
        string="Magento Address Bindings",
    )

    is_from_magento = fields.Boolean(string=("Magento Customer"), default=False)

    magento_id = fields.Integer()
    magento_customer_id = fields.Integer()
    magento_address_id = fields.Integer()
    backend_id = fields.Integer()


class ResPartnerCategory(models.Model):
    _inherit = 'res.partner.category'

    magento_bind_ids = fields.One2many(
        'magento.res.partner.category',
        'odoo_id',
        string='Magento Bindings',
        readonly=True,
    )
