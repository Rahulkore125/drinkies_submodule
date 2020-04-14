from odoo import models, fields


class MagentoStoreview(models.Model):
    _name = 'magento.storeview'
    _inherit = 'magento.binding'
    _description = "Magento Storeview"
    _order = 'sort_order ASC, id ASC'

    name = fields.Char(required=True, readonly=True)
    code = fields.Char()

    sort_order = fields.Integer(string='Sort Order', readonly=True)
    store_id = fields.Many2one('magento.store',
                               string='Store',
                               ondelete='cascade',
                               readonly=True)
    website_id = fields.Many2one('magento.website', string='Website')

    is_active = fields.Integer(string='Is active')
