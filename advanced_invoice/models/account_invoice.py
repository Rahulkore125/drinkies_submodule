from odoo import models, fields


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    original_invoice = fields.Boolean()
    order_id = fields.Integer()
