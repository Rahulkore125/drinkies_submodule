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
            # extend to update quant product to magento
            for move in picking.move_lines:
                for move_line in move.move_line_ids:
                    # update quant of source location (apply when type picking = outgoing or internal)
                    if picking.picking_type_id.code in ['outgoing', 'internal']:
                        if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                            for product in move_line.product_id.product_tmpl_id.product_variant_ids:
                                # get old quant of product
                                amount_old_quant = 0
                                if picking.location_id.magento_source_code:
                                    old_quant = self.env['stock.quant'].sudo().search(
                                        [('product_id', '=', product.id), ('location_id', '=', picking.location_id.id)])
                                    if old_quant:
                                        amount_old_quant = old_quant.quantity

                                if product.is_magento_product and picking.location_id.is_from_magento:
                                    magento_backend = self.env['magento.backend'].search([])
                                    try:
                                        params = {
                                            "sourceItems": [
                                                {
                                                    "sku": product.default_code,
                                                    "source_code": picking.location_id.magento_source_code,
                                                    "quantity": (
                                                                amount_old_quant - move_line.qty_done * move_line.product_id.deduct_amount_parent_product / product.deduct_amount_parent_product),
                                                    "status": 1
                                                }
                                            ]
                                        }
                                        client = Client(magento_backend.web_url, magento_backend.access_token, True)
                                        client.post('rest/V1/inventory/source-items', arguments=params)

                                    except Exception as a:
                                        raise UserError(
                                            ('Can not update quantity product on source magento - %s') % tools.ustr(a))
                        else:
                            if move_line.product_id.is_magento_product and picking.location_id.is_from_magento:
                                # get old quant of product
                                amount_old_quant = 0
                                if picking.location_id.magento_source_code:
                                    old_quant = self.env['stock.quant'].sudo().search(
                                        [('product_id', '=', move_line.product_id.id),
                                         ('location_id', '=', picking.location_id.id)])
                                    if old_quant:
                                        amount_old_quant = old_quant.quantity
                                magento_backend = self.env['magento.backend'].search([])
                                try:
                                    params = {
                                        "sourceItems": [
                                            {
                                                "sku": move_line.product_id.default_code,
                                                "source_code": picking.location_id.magento_source_code,
                                                "quantity": amount_old_quant - move_line.qty_done,
                                                "status": 1
                                            }
                                        ]
                                    }

                                    client = Client(magento_backend.web_url, magento_backend.access_token, True)
                                    client.post('rest/V1/inventory/source-items', arguments=params)

                                except Exception as a:
                                    raise UserError(
                                        ('Can not update quantity product on source magento - %s') % tools.ustr(a))
                    # update quant of dest location (apply when type = incoming or internal)
                    if picking.picking_type_id.code in ['incoming', 'internal']:
                        if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                            for product in move_line.product_id.product_tmpl_id.product_variant_ids:
                                # get old quant of product
                                amount_old_quant = 0
                                if picking.location_dest_id.magento_source_code:
                                    old_quant = self.env['stock.quant'].sudo().search([('product_id', '=', product.id),
                                                                                       ('location_id', '=',
                                                                                        picking.location_dest_id.id)])
                                    if old_quant:
                                        amount_old_quant = old_quant.quantity

                                if product.is_magento_product and picking.location_dest_id.is_from_magento:
                                    magento_backend = self.env['magento.backend'].search([])
                                    try:
                                        params = {
                                            "sourceItems": [
                                                {
                                                    "sku": product.default_code,
                                                    "source_code": picking.location_dest_id.magento_source_code,
                                                    "quantity": amount_old_quant + move_line.qty_done * move_line.product_id.deduct_amount_parent_product / product.deduct_amount_parent_product,
                                                    "status": 1
                                                }
                                            ]
                                        }
                                        client = Client(magento_backend.web_url, magento_backend.access_token, True)
                                        client.post('rest/V1/inventory/source-items', arguments=params)

                                    except Exception as a:
                                        raise UserError(
                                            ('Can not update quantity product on source magento - %s') % tools.ustr(a))
                        else:
                            if move_line.product_id.is_magento_product and picking.location_dest_id.is_from_magento:
                                # get old quant of product
                                amount_old_quant = 0
                                if picking.location_dest_id.magento_source_code:
                                    old_quant = self.env['stock.quant'].sudo().search(
                                        [('product_id', '=', move_line.product_id.id),
                                         ('location_id', '=', picking.location_dest_id.id)])
                                    if old_quant:
                                        amount_old_quant = old_quant.quantity
                                magento_backend = self.env['magento.backend'].search([])
                                try:
                                    params = {
                                        "sourceItems": [
                                            {
                                                "sku": move_line.product_id.default_code,
                                                "source_code": picking.location_dest_id.magento_source_code,
                                                "quantity": move_line.qty_done + amount_old_quant,
                                                "status": 1
                                            }
                                        ]
                                    }

                                    client = Client(magento_backend.web_url, magento_backend.access_token, True)
                                    client.post('rest/V1/inventory/source-items', arguments=params)

                                except Exception as a:
                                    raise UserError(
                                        ('Can not update quantity product on source magento - %s') % tools.ustr(a))
            if picking._check_backorder():
                pick_to_backorder |= picking
                continue
            pick_to_do |= picking
        # Process every picking that do not require a backorder, then return a single backorder wizard for every other ones.
        if pick_to_do:
            pick_to_do.action_done()
        if pick_to_backorder:
            return pick_to_backorder.action_generate_backorder_wizard()
        return False
