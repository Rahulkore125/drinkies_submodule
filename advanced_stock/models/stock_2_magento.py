from datetime import datetime

from odoo import models


class StockToMagento(models.TransientModel):
    _name = "stock.to.magento"

    def sync_quantity_to_magento(self, location_id, product_id, client):
        # if product_id.is_magento_product and location_id.is_from_magento:
        #     new_quanty_stock = self.env['stock.quant'].sudo().search(
        #         [('location_id', '=', location_id.id), ('product_id', '=', product_id.id)])
        #     if new_quanty_stock:
        #         try:
        #             params = {
        #                 "sourceItems": [
        #                     {
        #                         "sku": product_id.default_code,
        #                         "source_code": location_id.magento_source_code,
        #                         "quantity": new_quanty_stock.quantity,
        #                         "status": 1
        #                     }
        #                 ]
        #             }
        #             client.post('rest/V1/inventory/source-items', arguments=params)
        #         except Exception as a:
        #             traceback.print_exc(None, sys.stderr)
        #             self.env.cr.execute("""INSERT INTO trace_back_information (time_log, infor)
        #                                                                            VALUES (%s, %s)""",
        #                                 (datetime.now(), str(traceback.format_exc())))
        #             self.env.cr.commit()
        #             raise UserError(
        #                 ('Can not update quantity product on source magento - %s') % tools.ustr(a))
        pass

    def force_update_inventory_special_keg(self, location_id, location_dest_id, multiple_sku_tmpl, client, type):
        if type in ['incoming', 'outgoing','adjustment']:
            for e in multiple_sku_tmpl:
                product_tmpl = self.env['product.template'].search([('id', '=', e)])
                list_inventory_line = []
                for key in product_tmpl.product_variant_ids:
                    inventory_line = self.env['stock.inventory.line'].sudo().create({
                        'product_id': key.id,
                        'location_id': location_id.id,
                        'unit_real_qty': multiple_sku_tmpl[e] / key.deduct_amount_parent_product,
                    })
                    list_inventory_line.append(inventory_line.id)

                stock_inventory = self.env['stock.inventory'].create({
                    'name': 'Update other variant of ' + product_tmpl.name,
                    'location_id': location_id.id,
                    'date': datetime.now(),
                    'filter': 'partial',
                    'state': 'draft',
                    'line_ids': [(6, 0, list_inventory_line)]
                })

                # self.sync_quantity_to_magento(location_id=location_id, product_id=product_id, client=client)
                stock_inventory.sudo()._action_done(force_done_variant=True)

        if type in ['internal']:
            for e in multiple_sku_tmpl:
                product_tmpl = self.env['product.template'].search([('id', '=', e)])
                # update increase stock
                list_inventory_line = []
                for key in product_tmpl.product_variant_ids:
                    inventory_line = self.env['stock.inventory.line'].sudo().create({
                        'product_id': key.id,
                        'location_id': location_dest_id.id,
                        'unit_real_qty': multiple_sku_tmpl[e]['increase'] / key.deduct_amount_parent_product,
                    })
                    list_inventory_line.append(inventory_line.id)

                stock_inventory = self.env['stock.inventory'].create({
                    'name': 'Update other variant of ' + product_tmpl.name,
                    'location_id': location_dest_id.id,
                    'date': datetime.now(),
                    'filter': 'partial',
                    'state': 'draft',
                    'line_ids': [(6, 0, list_inventory_line)]
                })

                stock_inventory.sudo()._action_done(force_done_variant=True)

                # update decrease stock
                list_inventory_line = []
                for key in product_tmpl.product_variant_ids:
                    inventory_line = self.env['stock.inventory.line'].sudo().create({
                        'product_id': key.id,
                        'location_id': location_id.id,
                        'unit_real_qty': multiple_sku_tmpl[e]['decrease'] / key.deduct_amount_parent_product,
                    })
                    list_inventory_line.append(inventory_line.id)

                stock_inventory = self.env['stock.inventory'].create({
                    'name': 'Update other variant of ' + product_tmpl.name,
                    'location_id': location_id.id,
                    'date': datetime.now(),
                    'filter': 'partial',
                    'state': 'draft',
                    'line_ids': [(6, 0, list_inventory_line)]
                })
                stock_inventory.sudo()._action_done(force_done_variant=True)
