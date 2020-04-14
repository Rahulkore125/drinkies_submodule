from odoo import models, fields


class MagentoAccountInvoice(models.Model):
    _name = 'magento.account.invoice'
    _inherits = {'account.invoice': 'odoo_id'}
    _inherit = 'magento.binding'
    _description = 'Magento Invoice'
    _rec_name = 'number'

    odoo_id = fields.Many2one('account.invoice',
                              string='Invoice',
                              required=True,
                              ondelete='cascade')
    magento_order_id = fields.Many2one('magento.sale.order',
                                       string='Magento Sale Order',
                                       ondelete='set null')

    state = fields.Char("state")
