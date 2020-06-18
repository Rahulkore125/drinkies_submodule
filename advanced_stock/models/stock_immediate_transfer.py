from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_utils, float_compare
from ...magento2_connector.utils.magento.rest import Client
from odoo import tools, _


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
            pick_to_do.action_done()
            ## after action_done(), sync stock to magento
            stock2magento = self.env['stock.to.magento']
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            for pick in pick_to_do:
                for move in pick.move_lines:
                    if pick.picking_type_id.code in ['outgoing', 'internal']:
                        for move_line in move.move_line_ids:
                            if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                                stock2magento.force_update_inventory_special_keg(location_id=pick.location_id,
                                                                       product_id=move_line.product_id, client=client)
                            else:
                                stock2magento.sync_quantity_to_magento(location_id=pick.location_id,
                                                                       product_id=move_line.product_id, client=client)

                    if pick.picking_type_id.code in ['incoming', 'internal']:
                        for move_line in move.move_line_ids:
                            if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                                stock2magento.force_update_inventory_special_keg(location_id=pick.location_dest_id,
                                                                       product_id=move_line.product_id, client=client)
                            else:
                                stock2magento.sync_quantity_to_magento(location_id=pick.location_dest_id,
                                                                       product_id=move_line.product_id, client=client)

        if pick_to_backorder:
            return pick_to_backorder.action_generate_backorder_wizard()
        return False
