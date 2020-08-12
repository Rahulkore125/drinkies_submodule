from datetime import date

from odoo import fields, models, api
from ...magento2_connector.utils.magento.rest import Client


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    date_done_delivery = fields.Date()
    is_return_picking = fields.Boolean(default=False)
    has_return_picking = fields.Boolean(default=False)
    date_return = fields.Date()


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        for wizard in self:
            new_picking_id, pick_type_id = super(StockReturnPicking, wizard)._create_returns()
            # Override the context to disable all the potential filters that could have been set previously
        ctx = dict(self.env.context)

        ctx.update({
            'search_default_picking_type_id': pick_type_id,
            'search_default_draft': False,
            'search_default_assigned': False,
            'search_default_confirmed': False,
            'search_default_ready': False,
            'search_default_late': False,
            'search_default_available': False,
        })

        picking = self.env['stock.picking'].search([('id', '=', new_picking_id)])
        multiple_sku_tmpl = {}
        for move_line in picking.move_line_ids_without_package:
            if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                if move_line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                    multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id] = \
                        multiple_sku_tmpl[
                            move_line.product_id.product_tmpl_id.id] + move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product
                else:
                    variant_manage_stock = move_line.product_id.product_tmpl_id.variant_manage_stock
                    original_quantity = self.env['stock.quant'].search(
                        [('location_id', '=', picking.location_dest_id.id),
                         ('product_id', '=', variant_manage_stock.id)])
                    multiple_sku_tmpl[
                        move_line.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product + move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product
        for move_line in picking.move_lines:
            move_line.quantity_done = move_line.product_uom_qty
        picking.action_done()
        picking.is_return_picking = True

        picking.date_return = date.today()

        origin_picking = self.env['stock.picking'].search(
            [('id', '=', wizard.picking_id.id)])
        origin_picking.has_return_picking = True

        self.env.cr.execute(
            """UPDATE sale_order SET state = %s WHERE id = %s""", ('cancel', picking.sale_id.id))

        magento_backend = self.env['magento.backend'].search([], limit=1)
        client = Client(magento_backend.web_url, magento_backend.access_token, True)
        if len(multiple_sku_tmpl) > 0:
            stock2magento = self.env['stock.to.magento']
            stock2magento.force_update_inventory_special_keg(location_id=picking.location_dest_id,
                                                             location_dest_id=False,
                                                             multiple_sku_tmpl=multiple_sku_tmpl, client=client,
                                                             type='incoming')

        action = self.env['sale.order'].browse(picking.sale_id.id).action_view_delivery()

        return action


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)", copy=False,
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order',
                               default=True)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def _get_scrap_uom(self):
        unit_measure = self.env.ref('uom.product_uom_unit').id
        return unit_measure

    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        required=True, states={'done': [('readonly', True)]}, domain=lambda self: self._get_domain_product_uom_id(),
        default=lambda self: self._get_scrap_uom())
    date_scrap = fields.Date()

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            pass

    @api.onchange('product_id')
    def _get_domain_product_uom_id(self):
        unit_measure = self.env.ref('uom.product_uom_unit').id
        # product_uom = self.product_id.uom_id.id
        return {'domain': {'product_uom_id': [('id', 'in', [unit_measure])]}}

    def action_validate(self):
        self.date_scrap = date.today()

        multiple_sku_tmpl = {}
        if self.product_id.product_tmpl_id.multiple_sku_one_stock:
            variant_manage_stock = self.product_id.product_tmpl_id.variant_manage_stock
            original_quantity = self.env['stock.quant'].search(
                [('location_id', '=', self.location_id.id),
                 ('product_id', '=', variant_manage_stock.id)])
            multiple_sku_tmpl[
                self.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product - self.scrap_qty / self.product_id.uom_id.factor_inv * self.product_id.deduct_amount_parent_product

        a = super(StockScrap, self).action_validate()
        if len(multiple_sku_tmpl) > 0:
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            if len(multiple_sku_tmpl) > 0:
                stock2magento = self.env['stock.to.magento']
                stock2magento.force_update_inventory_special_keg(location_id=self.location_id,
                                                                 location_dest_id=False,
                                                                 multiple_sku_tmpl=multiple_sku_tmpl, client=client,
                                                                 type='outgoing')

        return a
