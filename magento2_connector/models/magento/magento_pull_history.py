from odoo import fields, models


class MagentoPullHistory(models.Model):
    """ customers,sale_orders,invoices,products"""

    _name = "magento.pull.history"
    _inherit = 'magento.binding'

    name = fields.Char()
    sync_date = fields.Datetime()
