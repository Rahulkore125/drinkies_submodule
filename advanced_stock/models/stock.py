from odoo import models, api, fields
from odoo import tools, _
from odoo.addons import decimal_precision as dp
from odoo.tools import float_utils
from ...magento2_connector.utils.magento.rest import Client
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


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

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
                                  strict=False):
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=strict)
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id,
                                                              package_id=package_id, owner_id=owner_id, strict=strict)
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_(
                    'It is not possible to reserve more products of %s than you have in stock.') % product_id.display_name)
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            print(quantity)
            print(available_quantity)
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                # raise UserError(_(
                #     'It is not possible to unreserve more products of %s than you have in stock.') % product_id.display_name)
                pass
        else:
            return reserved_quants

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity,
                                                                                     precision_rounding=rounding):
                break
        return reserved_quants


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
                multiple_sku_tmpl = {}
                for line in self.line_ids:
                    if line.product_id.product_tmpl_id.multiple_sku_one_stock:
                        if line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                            multiple_sku_tmpl[
                                line.product_id.product_tmpl_id.id] = line.product_qty * line.product_id.deduct_amount_parent_product
                        else:
                            multiple_sku_tmpl[
                                line.product_id.product_tmpl_id.id] = line.product_qty * line.product_id.deduct_amount_parent_product
                magento_backend = self.env['magento.backend'].search([], limit=1)
                client = Client(magento_backend.web_url, magento_backend.access_token, True)
                if len(multiple_sku_tmpl) > 0:
                    stock2magento = self.env['stock.to.magento']
                    stock2magento.force_update_inventory_special_keg(location_id=self.location_id,
                                                                     location_dest_id=False,
                                                                     multiple_sku_tmpl=multiple_sku_tmpl,
                                                                     client=client, type='adjustment')

            return True

    def action_check(self):
        """ Checks the inventory and computes the stock move to do """
        # tde todo: clean after _generate_moves
        for inventory in self.filtered(lambda x: x.state not in ('done', 'cancel')):
            # first remove the existing stock moves linked to this inventory
            inventory.mapped('move_ids').unlink()
            inventory.line_ids._generate_moves()


class InventoryLine(models.Model):
    _inherit = 'stock.inventory.line'

    unit_theoretical_qty = fields.Float('Theoretical Quantity by Unit', compute='_compute_unit_theoretical_qty',
                                        store=True)
    unit_real_qty = fields.Float('Real Quantity by Unit')
    product_qty = fields.Float(
        'Checked Quantity',
        digits=dp.get_precision('Product Unit of Measure'), default=0, compute='_compute_real_quantity', store=True)

    @api.multi
    def _compute_unit_theoretical_qty(self):
        for rec in self:
            rec.unit_theoretical_qty = rec.theoretical_qty * rec.product_uom_id.factor_inv

    @api.multi
    @api.depends('unit_real_qty')
    def _compute_real_quantity(self):
        for rec in self:
            if rec.product_uom_id.factor_inv:
                rec.product_qty = rec.unit_real_qty / rec.product_uom_id.factor_inv

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


class StockMove(models.Model):
    _inherit = 'stock.move'

    unit_real_qty = fields.Float('Real Quantity by Unit', default=0.0, readonly=False, compute='_compute_uom_quantity',
                                 store=True)
    product_uom_qty = fields.Float(
        'Initial Demand',
        digits=dp.get_precision('Product Unit of Measure'),
        default=0.0, required=True, states={'done': [('readonly', True)]},
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")

    @api.multi
    @api.onchange('unit_real_qty')
    def _compute_real_quantity(self):
        for rec in self:
            if rec.product_uom.factor_inv:
                rec.product_uom_qty = rec.unit_real_qty / rec.product_uom.factor_inv

    @api.multi
    @api.depends('product_uom_qty')
    def _compute_uom_quantity(self):
        for rec in self:
            if rec.product_uom.factor_inv:
                rec.unit_real_qty = rec.product_uom_qty * rec.product_uom.factor_inv


class StockLocation(models.Model):
    _inherit = 'stock.location'

    in_report = fields.Boolean("Is in Report?")
