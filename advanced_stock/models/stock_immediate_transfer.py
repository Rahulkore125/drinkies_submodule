from odoo import _
from odoo import models
from odoo.exceptions import UserError
from ...magento2_connector.utils.magento.rest import Client


class StockImmediateTransferInherit(models.TransientModel):
    _inherit = 'stock.immediate.transfer'
    _description = 'Immediate Transfer'

    def process(self):
        pick_to_backorder = self.env['stock.picking']
        pick_to_do = self.env['stock.picking']
        for picking in self.pick_ids:
            # If still in draft => confirm and assign
            if picking.state == 'draft':
                picking.action_confirm()
                if picking.state != 'assigned':
                    picking.action_assign()
                    if picking.state != 'assigned':
                        raise UserError(_(
                            "Could not reserve all requested products. Please use the \'Mark as Todo\' button to handle the reservation manually."))
            for move in picking.move_lines.filtered(lambda m: m.state not in ['done', 'cancel']):
                for move_line in move.move_line_ids:
                    move_line.qty_done = move_line.product_uom_qty
            if picking._check_backorder():
                pick_to_backorder |= picking
                continue
            pick_to_do |= picking
        # Process every picking that do not require a backorder, then return a single backorder wizard for every other ones.

        if pick_to_do:
            stock2magento = self.env['stock.to.magento']
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            for pick in pick_to_do:
                # handle case outgoing transfer
                if pick.picking_type_id.code in ['outgoing']:
                    multiple_sku_tmpl = {}
                    for move_line in pick.move_line_ids_without_package:
                        if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                            if move_line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                                multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id] = \
                                    multiple_sku_tmpl[
                                        move_line.product_id.product_tmpl_id.id] - move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product
                            else:
                                variant_manage_stock = move_line.product_id.product_tmpl_id.variant_manage_stock
                                original_quantity = self.env['stock.quant'].search(
                                    [('location_id', '=', pick.location_id.id),
                                     ('product_id', '=', variant_manage_stock.id)])
                                multiple_sku_tmpl[
                                    move_line.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product - move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product
                                # update stock for variant of multiple sku one stock
                    pick_to_do.action_done()
                    magento_backend = self.env['magento.backend'].search([], limit=1)
                    client = Client(magento_backend.web_url, magento_backend.access_token, True)
                    if len(multiple_sku_tmpl) > 0:
                        stock2magento = self.env['stock.to.magento']
                        stock2magento.force_update_inventory_special_keg(location_id=pick.location_id,
                                                                         location_dest_id=pick.location_dest_id,
                                                                         multiple_sku_tmpl=multiple_sku_tmpl,
                                                                         client=client, type='outgoing')

                # handle case internal transfer
                if pick.picking_type_id.code in ['internal']:
                    multiple_sku_tmpl = {}
                    for move_line in pick.move_line_ids_without_package:
                        if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                            if move_line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                                multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id]['decrease'] = \
                                    multiple_sku_tmpl[
                                        move_line.product_id.product_tmpl_id.id][
                                        'decrease'] - move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                                multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id]['increase'] = \
                                    multiple_sku_tmpl[
                                        move_line.product_id.product_tmpl_id.id][
                                        'increase'] + move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                            else:
                                variant_manage_stock = move_line.product_id.product_tmpl_id.variant_manage_stock
                                multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id] = {}
                                # get decrease quantity after transfer
                                original_decrease_quantity = self.env['stock.quant'].search(
                                    [('location_id', '=', pick.location_id.id),
                                     ('product_id', '=', variant_manage_stock.id)])
                                multiple_sku_tmpl[
                                    move_line.product_id.product_tmpl_id.id][
                                    'decrease'] = original_decrease_quantity.quantity * variant_manage_stock.deduct_amount_parent_product - move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                                # get_increase_quantity_after_transfer
                                original_increase_quantity = self.env['stock.quant'].search(
                                    [('location_id', '=', pick.location_dest_id.id),
                                     ('product_id', '=', variant_manage_stock.id)])
                                multiple_sku_tmpl[
                                    move_line.product_id.product_tmpl_id.id][
                                    'increase'] = original_increase_quantity.quantity * variant_manage_stock.deduct_amount_parent_product + move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                    pick_to_do.action_done()
                    magento_backend = self.env['magento.backend'].search([], limit=1)
                    client = Client(magento_backend.web_url, magento_backend.access_token, True)
                    if len(multiple_sku_tmpl) > 0:
                        stock2magento = self.env['stock.to.magento']
                        stock2magento.force_update_inventory_special_keg(location_id=pick.location_id,
                                                                         location_dest_id=pick.location_dest_id,
                                                                         multiple_sku_tmpl=multiple_sku_tmpl,
                                                                         client=client, type='internal')
                # handle case incoiming transfer
                if pick.picking_type_id.code in ['incoming']:
                    multiple_sku_tmpl = {}
                    for move_line in pick.move_line_ids_without_package:
                        if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                            if move_line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                                multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id] = \
                                    multiple_sku_tmpl[
                                        move_line.product_id.product_tmpl_id.id] + move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product
                            else:
                                variant_manage_stock = move_line.product_id.product_tmpl_id.variant_manage_stock
                                original_quantity = self.env['stock.quant'].search(
                                    [('location_id', '=', pick.location_dest_id.id),
                                     ('product_id', '=', variant_manage_stock.id)])
                                multiple_sku_tmpl[
                                    move_line.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product + move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product
                                # update stock for variant of multiple sku one stock
                    pick_to_do.action_done()
                    magento_backend = self.env['magento.backend'].search([], limit=1)
                    client = Client(magento_backend.web_url, magento_backend.access_token, True)
                    if len(multiple_sku_tmpl) > 0:
                        stock2magento = self.env['stock.to.magento']
                        stock2magento.force_update_inventory_special_keg(location_id=pick.location_dest_id,
                                                                         location_dest_id=pick.location_dest_id,
                                                                         multiple_sku_tmpl=multiple_sku_tmpl,
                                                                         client=client, type='incoming')
        if pick_to_backorder:
            return pick_to_backorder.action_generate_backorder_wizard()
        return False
