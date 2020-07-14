from odoo import models, api, tools, fields
from odoo.tools import float_utils, float_compare
from ...magento2_connector.utils.magento.rest import Client
from odoo import tools, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp

class ProductChangeQuantity(models.TransientModel):
    _inherit = "stock.change.product.qty"

    @api.constrains('new_quantity')
    def check_new_quantity(self):
        if any(wizard.new_quantity < 0 for wizard in self):
            pass

    def change_product_qty(self):
        """ Changes the Product Quantity by making a Physical Inventory. """
        Inventory = self.env['stock.inventory']
        for wizard in self:
            product = wizard.product_id.with_context(location=wizard.location_id.id)
            line_data = wizard._action_start_line()

            if wizard.product_id.id:
                inventory_filter = 'product'
            else:
                inventory_filter = 'none'
            inventory = Inventory.create({
                'name': _('INV: %s') % tools.ustr(wizard.product_id.display_name),
                'filter': inventory_filter,
                'product_id': wizard.product_id.id,
                'location_id': wizard.location_id.id,
                'line_ids': [(0, 0, line_data)],
            })
            if wizard.location_id.is_from_magento:
                pass
            inventory.action_validate()
        product = self.env['product.product'].search([('id', '=', line_data['product_id'])])
        if product.product_tmpl_id.multiple_sku_one_stock:
            product.product_tmpl_id.origin_quantity = line_data['product_qty'] * product.deduct_amount_parent_product

        return {'type': 'ir.actions.act_window_close'}


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    original_qty = fields.Float(string="Origin Quantity", default=0)
    updated_qty = fields.Boolean(default=False)


class Inventory(models.Model):
    _inherit = "stock.inventory"

    update_to_magento = fields.Boolean(default=False)

    def _action_done(self, force_done_variant=False):
        if force_done_variant:
            self.action_check()
            self.write({'state': 'done'})
            self.post_inventory()
            ## after action_done(), sync stock to magento
            stock2magento = self.env['stock.to.magento']
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            for line in self.line_ids:
                stock2magento.sync_quantity_to_magento(location_id=self.location_id,
                                                       product_id=line.product_id, client=client)
            return True
        else:
            self.action_check()
            self.write({'state': 'done'})
            self.post_inventory()
            ##check special product in stock_inventory
            if self.line_ids:
                for line in self.line_ids:
                    ## after action_done(), sync stock to magento
                    stock2magento = self.env['stock.to.magento']
                    magento_backend = self.env['magento.backend'].search([], limit=1)
                    client = Client(magento_backend.web_url, magento_backend.access_token, True)
                    if line.product_id.product_tmpl_id.multiple_sku_one_stock:
                        stock2magento.force_update_inventory_special_keg(location_id=self.location_id,
                                                                         product_id=line.product_id, client=client)
                    else:
                        stock2magento.sync_quantity_to_magento(location_id=self.location_id,
                                                               product_id=line.product_id, client=client)
                # for e in self.line_ids:
                #     if e.product_id.product_tmpl_id.multiple_sku_one_stock:
                #         stock_quant = self.env['stock.quant'].search(
                #             [('location_id', '=', self.location_id.id),
                #              ('product_id', '=', e.product_id.product_tmpl_id.variant_manage_stock.id)])
                #
                #         if stock_quant.original_qty != e.product_qty * e.product_id.deduct_amount_parent_product:
                #             stock_quant.sudo().write({
                #                 'updated_qty': True,
                #                 'original_qty': e.product_qty * e.product_id.deduct_amount_parent_product
                #             })

            return True

    # def action_validate(self):
    #     res = super(Inventory, self).action_validate()
    #
    #     return res

    def action_check(self):
        """ Checks the inventory and computes the stock move to do """
        # tde todo: clean after _generate_moves
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            # first remove the existing stock moves linked to this inventory
            inventory.mapped('move_ids').unlink()
            inventory.line_ids._generate_moves()


class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    unit_theoretical_qty = fields.Float('Theoretical Quantity by Unit', compute='_compute_unit_theoretical_qty', store=True)
    unit_real_qty = fields.Float('Real Quantity by Unit')
    product_qty = fields.Float(
        'Checked Quantity',
        digits=dp.get_precision('Product Unit of Measure'), default=0, compute='_compute_real_quantity', store= True)

    @api.multi
    def _compute_unit_theoretical_qty(self):
        for rec in self:
            rec.unit_theoretical_qty = rec.theoretical_qty*rec.product_uom_id.factor_inv

    @api.multi
    @api.depends('unit_real_qty')
    def _compute_real_quantity(self):
        for rec in self:
            if rec.product_uom_id.factor_inv:
                rec.product_qty = rec.unit_real_qty/rec.product_uom_id.factor_inv

    @api.multi
    @api.depends('theoretical_qty')
    def _compute_unit_theoretical_qty(self):
        for rec in self:
            if rec.product_uom_id.factor_inv:
                rec.unit_theoretical_qty = rec.theoretical_qty * rec.product_uom_id.factor_inv

    def _generate_moves(self):
        vals_list = []
        for line in self:
            if float_utils.float_compare(line.theoretical_qty, line.product_qty,
                                         precision_rounding=line.product_id.uom_id.rounding) == 0:
                continue
            diff = line.theoretical_qty - line.product_qty
            if diff < 0:  # found more than expected
                vals = line._get_move_values(abs(diff), line.product_id.property_stock_inventory.id,
                                             line.location_id.id, False)
            else:
                vals = line._get_move_values(abs(diff), line.location_id.id,
                                             line.product_id.property_stock_inventory.id, True)
            vals_list.append(vals)
        return self.env['stock.move'].create(vals_list)
