from odoo import api, fields, models, tools
from odoo.exceptions import UserError
import sys
import traceback
from datetime import datetime


class StockToMagento(models.TransientModel):
    _name = "stock.to.magento"

    def sync_quantity_to_magento(self, location_id, product_id, client):
        # pass
        if product_id.product_tmpl_id.multiple_sku_one_stock:
            # step1: update variant_manage_stock product quantity
            stock_quant_current_product = self.env['stock.quant'].search(
                [('location_id', '=', location_id.id), ('product_id', '=', product_id.id)])
            stock_of_variant_manage_stock = self.env['stock.quant'].search(
                [('location_id', '=', location_id.id),
                 ('product_id', '=', product_id.product_tmpl_id.variant_manage_stock.id)])
            stock_of_variant_manage_stock.sudo().write({
                'updated_qty': True,
                'quantity': stock_quant_current_product.quantity * product_id.deduct_amount_parent_product
            })
            for product_variant in product_id.product_tmpl_id.product_variant_ids:
                ## step2 update quantity before update to magento
                old_stock_quant = self.env['stock.quant'].search(
                    [('location_id', '=', location_id.id), ('product_id', '=', product_variant.id)])
                stock_of_variant_manage_stock = self.env['stock.quant'].search(
                    [('location_id', '=', location_id.id),
                     ('product_id', '=', product_id.product_tmpl_id.variant_manage_stock.id)])
                if old_stock_quant:
                    old_stock_quant.sudo().write({
                        'updated_qty': True,
                        'quantity': stock_of_variant_manage_stock.quantity * (
                                product_id.product_tmpl_id.variant_manage_stock.deduct_amount_parent_product / product_variant.deduct_amount_parent_product)
                    })
                else:
                    self.env['stock.quant'].sudo().create({
                        'product_id': product_variant.id,
                        'location_id': location_id.id,
                        'updated_qty': True,
                        'quantity': stock_of_variant_manage_stock.quantity * (
                                product_id.product_tmpl_id.variant_manage_stock.deduct_amount_parent_product / product_variant.deduct_amount_parent_product)
                    })
                if product_variant.is_magento_product and location_id.is_from_magento:
                    try:
                        params = {
                            "sourceItems": [
                                {
                                    "sku": product_variant.default_code,
                                    "source_code": location_id.magento_source_code,
                                    "quantity": old_stock_quant.quantity,
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
        else:
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
