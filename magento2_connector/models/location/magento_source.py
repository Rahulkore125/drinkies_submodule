from odoo import fields, models


class MagentoSource(models.Model):
    _name = 'magento.source'
    _inherit = 'magento.binding'
    _inherits = {'stock.location': 'odoo_id'}
    _description = 'Magento Source'

    odoo_id = fields.Many2one('stock.location', string='Magento Source', required=True,
                              ondelete='cascade')

    website_id = fields.Many2one('magento.website',
                                 string='Magento Website',
                                 ondelete='restrict')
    storeview_id = fields.Many2one('magento.storeview', string='Magento Store View')
