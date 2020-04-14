from odoo import fields, models, api


class MagentoSaleOrder(models.Model):
    _name = 'magento.sale.order'
    _description = 'Magento Sale Order'
    _inherit = 'magento.binding'
    _inherits = {'sale.order': 'odoo_id'}

    odoo_id = fields.Many2one('sale.order',
                              string='Sale Order',
                              required=True,
                              ondelete='cascade')
    magento_order_line_ids = fields.One2many(
        'magento.sale.order.line',
        'magento_order_id',
        string='Magento Order Lines'
    )

    # magento_order_id = fields.Integer(string='Magento Order ID',
    #                                   help="'order_id' field in Magento")

    storeview_id = fields.Many2one('magento.storeview',
                                   string='Magento Storeview')
    store_id = fields.Many2one('storeview_id.store_id',
                               string='Storeview',
                               readonly=True)

    shipment_amount = fields.Float("Shipment Amount")
    shipment_method = fields.Char("Shipment Method")
    # state order on magento
    state = fields.Char("State")
    # status order on Odoo
    status = fields.Char("Status")

    @api.multi
    def preview_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.odoo_id.get_portal_url(),
        }

    @api.multi
    def action_view_invoice(self):
        return self.odoo_id.action_view_invoice()


class MagentoSaleOrderLine(models.Model):
    _name = 'magento.sale.order.line'
    _description = 'Magento Sale Order Line'
    _inherits = {'sale.order.line': 'odoo_id'}

    magento_order_id = fields.Many2one('magento.sale.order',
                                       'Magento Sale Order',
                                       required=True,
                                       ondelete='cascade',
                                       index=True)
    odoo_id = fields.Many2one('sale.order.line',
                              'Sale Order Line',
                              required=True,
                              ondelete='cascade')
