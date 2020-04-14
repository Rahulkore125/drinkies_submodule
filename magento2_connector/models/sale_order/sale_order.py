from odoo import fields, models, api
from odoo.tools import float_compare, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    magento_bind_ids = fields.One2many(
        'magento.sale.order',
        'odoo_id',
        string="Magento Bindings",
    )

    is_magento_sale_order = fields.Boolean("is_magento_sale_order")
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True,
                                  store=True)
    order_reference_id = fields.Char(store=True, readonly=False,
                                     string="Order Reference ID")

    # @api.multi
    # def action_view_invoice(self):
    #     if self.is_magento_sale_order:
    #         invoices = self.mapped('invoice_ids')
    #         action = self.env.ref('account.action_invoice_tree1').read()[0]
    #         if len(invoices) > 1:
    #             action['domain'] = [('id', 'in', invoices.ids)]
    #         elif len(invoices) == 1:
    #             action['views'] = [(self.env.ref('magento2_connector.invoice_form').id, 'form')]
    #             action['res_id'] = invoices.ids[0]
    #         else:
    #             action = {'type': 'ir.actions.act_window_close'}
    #         return action
    #     else:
    #         return super(SaleOrder, self).action_view_invoice()

    @api.multi
    @api.depends('order_line', 'estimate_discount_total')
    def compute_discount_total(self):
        for rec in self:
            sum = 0
            for e in rec.order_line:
                if e.is_reward_line:
                    sum += abs(e.price_subtotal)
                # print('dependes')
                if e.product_id.id == self.env.ref('magento2_connector.discount_record').id:
                    sum += abs(e.price_subtotal)
            sum += rec.estimate_discount_total
            rec.computed_discount_total = sum


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    magento_bind_ids = fields.One2many(
        'magento.sale.order.line',
        'odoo_id',
        string="Magento Bindings",
    )

    @api.multi
    def _action_launch_stock_rule(self):
        """
        Launch procurement group run method with required/custom fields genrated by a
        sale order line. procurement group will launch '_run_pull', '_run_buy' or '_run_manufacture'
        depending on the sale order line product rule.
        Over ride function from sale.order.line
        """
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        errors = []
        for line in self:
            if line.state != 'sale' or not line.product_id.type in ('magento_simple'):
                continue
            qty = line._get_qty_procurement()
            if float_compare(qty, line.product_uom_qty, precision_digits=precision) >= 0:
                continue

            group_id = line.order_id.procurement_group_id
            if not group_id:
                group_id = self.env['procurement.group'].create({
                    'name': line.order_id.name, 'move_type': line.order_id.picking_policy,
                    'sale_id': line.order_id.id,
                    'partner_id': line.order_id.partner_shipping_id.id,
                })
                line.order_id.procurement_group_id = group_id
            else:
                # In case the procurement group is already created and the order was
                # cancelled, we need to update certain values of the group.
                updated_vals = {}
                if group_id.partner_id != line.order_id.partner_shipping_id:
                    updated_vals.update({'partner_id': line.order_id.partner_shipping_id.id})
                if group_id.move_type != line.order_id.picking_policy:
                    updated_vals.update({'move_type': line.order_id.picking_policy})
                if updated_vals:
                    group_id.write(updated_vals)

            values = line._prepare_procurement_values(group_id=group_id)
            product_qty = line.product_uom_qty - qty

            procurement_uom = line.product_uom
            quant_uom = line.product_id.uom_id
            get_param = self.env['ir.config_parameter'].sudo().get_param
            if procurement_uom.id != quant_uom.id and get_param('stock.propagate_uom') != '1':
                product_qty = line.product_uom._compute_quantity(product_qty, quant_uom, rounding_method='HALF-UP')
                procurement_uom = quant_uom

            try:
                self.env['procurement.group'].run(line.product_id, product_qty, procurement_uom,
                                                  line.order_id.partner_shipping_id.property_stock_customer, line.name,
                                                  line.order_id.name, values)
            except UserError as error:
                errors.append(error.name)
        if errors:
            raise UserError('\n'.join(errors))
        return super(SaleOrderLine, self)._action_launch_stock_rule()
