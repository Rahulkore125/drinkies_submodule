from odoo import models, fields


class StockLocation(models.Model):
    _inherit = 'stock.location'

    magento_bind_ids = fields.One2many(
        'magento.source',
        'odoo_id',
        string="Magento Bindings",
    )

    is_from_magento = fields.Boolean(string=("Magento Source"), default=False)
    magento_source_code = fields.Char("Magento Source Code")
    postcode = fields.Char("Postcode")
