from odoo import fields, models


class MagentoResPartner(models.Model):
    _name = 'magento.res.partner'
    _inherit = 'magento.binding'
    _inherits = {'res.partner': 'odoo_id'}
    _description = 'Magento Partner'

    odoo_id = fields.Many2one('res.partner', string='Partner', required=True,
                              ondelete='cascade')

    website_id = fields.Many2one('magento.website',
                                 string='Magento Website',
                                 required=True,
                                 ondelete='restrict')
    storeview_id = fields.Many2one('magento.storeview', string='Magento Store View', required=True)
    group_id = fields.Many2one('magento.res.partner.category',
                               string='Magento Group (Category)')

    magento_address_ids = fields.One2many('magento.address', 'magento_partner_id', string='Magento Address')

    # created_at = fields.Datetime(string='Created At (on Magento)')
    # updated_at = fields.Datetime(string='Updated At (on Magento)')
    # gender_id = fields.Integer(string=_('Gender'))
    # birthday = fields.Date(string='Birthday')


class MagentoAddress(models.Model):
    _name = 'magento.address'
    _inherits = {'res.partner': 'odoo_id'}
    _inherit = 'magento.binding'
    _description = 'Magento Address'

    odoo_id = fields.Many2one('res.partner',
                              string='Partner',
                              required=True,
                              ondelete='cascade')

    magento_partner_id = fields.Many2one('magento.res.partner',
                                         string='Magento Partner',
                                         required=True,
                                         ondelete='cascade')

    website_id = fields.Many2one(
        'magento.website',
        related='magento_partner_id.website_id',
        string='Magento Website',
        store=True,
        readonly=True,
    )


class MagentoResPartnerCategory(models.Model):
    """ Customers Group"""
    _name = 'magento.res.partner.category'
    _inherit = 'magento.binding'
    _inherits = {'res.partner.category': 'odoo_id'}

    odoo_id = fields.Many2one('res.partner.category',
                              string='Partner Category',
                              required=True,
                              ondelete='cascade')
    # tax_class_id = fields.Integer(string=_('Tax class'))
    # tax_class_name = fields.Char(string=_('Name'))
