from odoo import api, fields, models, tools
from odoo.exceptions import UserError
import sys
import traceback
from datetime import datetime, date


class StockToMagento(models.TransientModel):
    _name = "stock.to.magento"

    def sync_quantity_to_magento(self, location_id, product_id, client):
        # if product_id.product_tmpl_id.multiple_sku_one_stock:
        #     stock_quant_current_product = self.env['stock.quant'].search(
        #         [('location_id', '=', location_id.id), ('product_id', '=', product_id.id)])
        #     # compute quant of varianmanager after update
        #     amount_after_after = stock_quant_current_product.quantity * (product_id.deduct_amount_parent_product / product_id.product_tmpl_id.variant_manage_stock.deduct_amount_parent_product)
        #     for product_variant in product_id.product_tmpl_id.product_variant_ids:
        #         if product_variant.is_magento_product and location_id.is_from_magento:
        #             try:
        #                 params = {
        #                     "sourceItems": [
        #                         {
        #                             "sku": product_variant.default_code,
        #                             "source_code": location_id.magento_source_code,
        #                             "quantity": amount_after_after * (product_id.product_tmpl_id.variant_manage_stock.deduct_amount_parent_product / product_variant.deduct_amount_parent_product),
        #                             "status": 1
        #                         }
        #                     ]
        #                 }
        #                 client.post('rest/V1/inventory/source-items', arguments=params)
        #
        #             except Exception as a:
        #                 traceback.print_exc(None, sys.stderr)
        #                 self.env.cr.execute("""INSERT INTO trace_back_information (time_log, infor)
        #                                                                                VALUES (%s, %s)""",
        #                                     (datetime.now(), str(traceback.format_exc())))
        #                 self.env.cr.commit()
        #                 raise UserError(
        #                     ('Can not update quantity product on source magento - %s') % tools.ustr(a))
        # else:
        if product_id.is_magento_product and location_id.is_from_magento:
            new_quanty_stock = self.env['stock.quant'].sudo().search(
                [('location_id', '=', location_id.id), ('product_id', '=', product_id.id)])
            if new_quanty_stock:
                try:
                    params = {
                        "sourceItems": [
                            {
                                "sku": product_id.default_code,
                                "source_code": location_id.magento_source_code,
                                "quantity": new_quanty_stock.quantity,
                                "status": 1
                            }
                        ]
                    }
                    client.post('rest/V1/inventory/source-items', arguments=params)
                except Exception as a:
                    traceback.print_exc(None, sys.stderr)
                    self.env.cr.execute("""INSERT INTO trace_back_information (time_log, infor)
                                                                                   VALUES (%s, %s)""",
                                        (datetime.now(), str(traceback.format_exc())))
                    self.env.cr.commit()
                    raise UserError(
                        ('Can not update quantity product on source magento - %s') % tools.ustr(a))

    def force_update_inventory_special_keg(self, location_id, product_id, client):
        # step1: compute all product variant quantity
        # get quant of product_id
        stock_quant_current_product = self.env['stock.quant'].search(
            [('location_id', '=', location_id.id), ('product_id', '=', product_id.id)])
        # compute quant of varianmanager after update
        amount_after_after = stock_quant_current_product.quantity * (product_id.deduct_amount_parent_product / product_id.product_tmpl_id.variant_manage_stock.deduct_amount_parent_product)
        dict_product_update = {}
        for product_variant in product_id.product_tmpl_id.product_variant_ids:
            if product_variant.id != product_id.id:
                dict_product_update[product_variant.id] = amount_after_after * (product_id.product_tmpl_id.variant_manage_stock.deduct_amount_parent_product / product_variant.deduct_amount_parent_product)
        list_inventory_line = []
        for key in dict_product_update:
            inventory_line = self.env['stock.inventory.line'].sudo().create({
                'product_id': key,
                'location_id': location_id.id,
                'product_qty': dict_product_update[key],
            })
            list_inventory_line.append(inventory_line.id)
        stock_inventory = self.env['stock.inventory'].create({
            'name': 'Update other variant of ' + product_id.name,
            'location_id': location_id.id,
            'date': datetime.now(),
            'filter': 'partial',
            'state': 'draft',
            'line_ids': [(6, 0, list_inventory_line)]
        })
        stock_inventory.sudo()._action_done(force_done_variant=True)
