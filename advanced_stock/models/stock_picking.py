from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_compare
from ...magento2_connector.utils.magento.rest import Client


class StockPickingInherit(models.Model):
    _inherit = "stock.picking"

    @api.multi
    def button_validate(self):
        res = super(StockPickingInherit, self).button_validate()
        ## after action_done(), sync stock to magento
        stock2magento = self.env['stock.to.magento']
        magento_backend = self.env['magento.backend'].search([], limit=1)
        client = Client(magento_backend.web_url, magento_backend.access_token, True)
        for move in self.move_lines:
            if self.picking_type_id.code in ['outgoing', 'internal']:
                for move_line in move.move_line_ids:
                    if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                        stock2magento.force_update_inventory_special_keg(location_id=self.location_id,
                                                                         product_id=move_line.product_id, client=client)
                    else:
                        stock2magento.sync_quantity_to_magento(location_id=self.location_id,
                                                               product_id=move_line.product_id, client=client)
            if self.picking_type_id.code in ['incoming', 'internal']:
                for move_line in move.move_line_ids:
                    if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                        stock2magento.force_update_inventory_special_keg(location_id=self.location_dest_id,
                                                                         product_id=move_line.product_id, client=client)
                    else:
                        stock2magento.sync_quantity_to_magento(location_id=self.location_dest_id,
                                                               product_id=move_line.product_id, client=client)
        return res
