from odoo import models, fields


class MagentoStore(models.Model):
    _name = 'magento.store'
    _inherit = 'magento.binding'
    _description = 'Magento Store'

    name = fields.Char()
    code = fields.Char()
    root_category_id = fields.Integer()

    website_id = fields.Many2one(
        'magento.website',
        string='Magento Website',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    storeview_ids = fields.One2many(
        'magento.storeview',
        'store_id',
        string="Storeviews",
        readonly=True,
    )
