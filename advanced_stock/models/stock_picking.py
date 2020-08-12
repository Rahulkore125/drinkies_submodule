from odoo import api, models
from ...magento2_connector.utils.magento.rest import Client


class StockPickingInherit(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def button_validate(self):
        ## after action_done(), sync stock to magento
        if self.picking_type_id.code in ['outgoing']:
            multiple_sku_tmpl = {}
            for move_line in self.move_line_ids_without_package:
                if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                    if move_line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                        multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id] = \
                            multiple_sku_tmpl[
                                move_line.product_id.product_tmpl_id.id] - move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                    else:
                        variant_manage_stock = move_line.product_id.product_tmpl_id.variant_manage_stock
                        original_quantity = self.env['stock.quant'].search(
                            [('location_id', '=', self.location_id.id),
                             ('product_id', '=', variant_manage_stock.id)])
                        multiple_sku_tmpl[
                            move_line.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product - move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                        # update stock for variant of multiple sku one stock
            res = super(StockPickingInherit, self).button_validate()
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            if len(multiple_sku_tmpl) > 0:
                stock2magento = self.env['stock.to.magento']
                stock2magento.force_update_inventory_special_keg(location_id=self.location_id,
                                                                 location_dest_id=self.location_dest_id,
                                                                 multiple_sku_tmpl=multiple_sku_tmpl,
                                                                 client=client, type='outgoing')

        if self.picking_type_id.code in ['internal']:
            multiple_sku_tmpl = {}
            for move_line in self.move_line_ids_without_package:
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
                            [('location_id', '=', self.location_id.id),
                             ('product_id', '=', variant_manage_stock.id)])
                        multiple_sku_tmpl[
                            move_line.product_id.product_tmpl_id.id][
                            'decrease'] = original_decrease_quantity.quantity * variant_manage_stock.deduct_amount_parent_product - move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                        # get_increase_quantity_after_transfer
                        original_increase_quantity = self.env['stock.quant'].search(
                            [('location_id', '=', self.location_dest_id.id),
                             ('product_id', '=', variant_manage_stock.id)])
                        multiple_sku_tmpl[
                            move_line.product_id.product_tmpl_id.id][
                            'increase'] = original_increase_quantity.quantity * variant_manage_stock.deduct_amount_parent_product + move_line.qty_done * move_line.product_id.deduct_amount_parent_product
            res = super(StockPickingInherit, self).button_validate()
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            if len(multiple_sku_tmpl) > 0:
                stock2magento = self.env['stock.to.magento']
                stock2magento.force_update_inventory_special_keg(location_id=self.location_id,
                                                                 location_dest_id=self.location_dest_id,
                                                                 multiple_sku_tmpl=multiple_sku_tmpl,
                                                                 client=client, type='internal')

        if self.picking_type_id.code in ['incoming']:
            multiple_sku_tmpl = {}
            for move_line in self.move_line_ids_without_package:
                if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                    if move_line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                        multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id] = \
                            multiple_sku_tmpl[
                                move_line.product_id.product_tmpl_id.id] + move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                    else:
                        variant_manage_stock = move_line.product_id.product_tmpl_id.variant_manage_stock
                        original_quantity = self.env['stock.quant'].search(
                            [('location_id', '=', self.location_dest_id.id),
                             ('product_id', '=', variant_manage_stock.id)])
                        multiple_sku_tmpl[
                            move_line.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product + move_line.qty_done * move_line.product_id.deduct_amount_parent_product
                        # update stock for variant of multiple sku one stock

            res = super(StockPickingInherit, self).button_validate()
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            if len(multiple_sku_tmpl) > 0:
                stock2magento = self.env['stock.to.magento']
                stock2magento.force_update_inventory_special_keg(location_id=self.location_dest_id,
                                                                 location_dest_id=self.location_dest_id,
                                                                 multiple_sku_tmpl=multiple_sku_tmpl,
                                                                 client=client, type='incoming')

        return res
