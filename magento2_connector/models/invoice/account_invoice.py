from odoo import fields, models


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    magento_bind_ids = fields.One2many(
        'magento.account.invoice',
        'odoo_id',
        string='Magento Bindings',
    )

    is_magento_invoice = fields.Boolean("is_magento_invoice")
