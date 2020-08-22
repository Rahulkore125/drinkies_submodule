from datetime import datetime, timedelta

from odoo import models, fields, _
from odoo.exceptions import UserError


class SaleHnkReport(models.Model):
    _name = 'sale.hnk.report'

    compute_at_date = fields.Selection([
        (0, 'At a Specific Date'),
        (1, 'At a Time Period')
    ], string="Compute", default=0)
    date_report = fields.Date(string="Date Report", default=fields.Date.today)
    from_date_report = fields.Date(string="From Date", default=fields.Date.today)
    to_date_report = fields.Date(string="To Date", default=fields.Date.today)
    report_line_ids = fields.One2many(comodel_name='sale.hnk.report.line', inverse_name='sale_report_id',
                                      string="Report Line")
    datetime_report = fields.Datetime(string="Datetime Report")
    location_id = fields.Many2one('stock.location', domain="[('is_from_magento', '=', True)]")

    def generate_report(self):
        a = self.env.user.tz_offset

        prefix = a.split('00')[0]

        if prefix[0] == '+':
            time_offset = int(prefix.split('+')[1])
        elif prefix[0] == '-':
            time_offset = - int(prefix.split('-')[1])

        values = []

        product_ids = {}

        sale = self.env.ref('advanced_sale.sale').id
        food_panda = self.env.ref('advanced_sale.food_panda').id
        grab = self.env.ref('advanced_sale.grab').id
        shopee = self.env.ref('advanced_sale.shopee').id
        pos = self.env.ref('advanced_sale.pos').id
        lazmall = self.env.ref('advanced_sale.lazmall').id
        pandamart = self.env.ref('advanced_sale.pandamart').id

        if self.compute_at_date == 1:
            if self.from_date_report >= self.to_date_report:
                raise UserError(_('Invalid data. From date can not great than or equal to date'))
            else:
                today_date = datetime(year=self.to_date_report.year, month=self.to_date_report.month,
                                      day=self.to_date_report.day, hour=24 - time_offset, minute=00, second=00)
                previous_day_date = datetime(year=self.from_date_report.year, month=self.from_date_report.month,
                                             day=self.from_date_report.day, hour=24 - time_offset, minute=00,
                                             second=00) + timedelta(days=-1)
                # print(today_date)
                # print(previous_day_date)
        elif self.compute_at_date == 0:
            today_date = datetime(year=self.date_report.year, month=self.date_report.month,
                                  day=self.date_report.day, hour=24 - time_offset, minute=00, second=00)
            previous_day_date = today_date + timedelta(days=-1)
            previous_day_date = datetime(previous_day_date.year, month=previous_day_date.month,
                                         day=previous_day_date.day, hour=24 - time_offset, minute=00, second=00)

        start_order_date = datetime(year=previous_day_date.year, month=previous_day_date.month,
                                    day=previous_day_date.day, hour=24 - time_offset, minute=00, second=00)

        end_order_date = datetime(year=today_date.year, month=today_date.month,
                                  day=today_date.day, hour=24 - time_offset, minute=00, second=00)
        if not self.location_id:
            sale_orders = self.env['sale.order'].search(
                [('delivery_date', '>=', start_order_date), ('delivery_date', '<', end_order_date),
                 ('state', '=', 'done')])
        else:
            sale_orders = self.env['sale.order'].search(
                [('delivery_date', '>=', start_order_date), ('delivery_date', '<', end_order_date),
                 ('state', '=', 'done'), ('location_id', '=', self.location_id.id)])

        heineken_product = self.env['product.product'].search([('is_heineken_product', '=', True)])
        magento_demo_simple_product = self.env.ref('magento2_connector.magento_sample_product_consumable')
        magento_demo_service_product = self.env.ref('magento2_connector.magento_sample_product_service')
        discount_product = self.env['product.product'].search([('is_discount_product', '=', True)])
        heineken_product += magento_demo_service_product
        heineken_product += magento_demo_simple_product
        heineken_product += discount_product

        qty_previous_day = self.with_context(location=self.location_id.id).env['product.product'].browse(
            heineken_product.ids)._compute_quantities_dict(
            self._context.get('lot_id'),
            self._context.get(
                'owner_id'),
            self._context.get(
                'package_id'),
            self._context.get(
                'from_date'),
            to_date=previous_day_date)

        # todo chua xu ly truong hop cac mui gio am.
        # print(qty_previous_day)
        qty_today = self.with_context(location=self.location_id.id).env['product.product'].browse(
            heineken_product.ids)._compute_quantities_dict(
            self._context.get('lot_id'),
            self._context.get(
                'owner_id'),
            self._context.get(
                'package_id'),
            self._context.get(
                'from_date'),
            to_date=today_date)

        for e in qty_today:
            product = self.env['product.product'].browse(e)
            precision = product.uom_id.factor_inv
            if e in product_ids:
                product_ids[e]['product_category_id'] = product.categ_id.id,
                product_ids[e]['close_stock'] = qty_today[e]['qty_available']
                product_ids[e]['open_stock'] = qty_previous_day[e]['qty_available']
                product_ids[e]['open_stock_units'] = product_ids[e]['open_stock'] * precision
                product_ids[e]['close_stock_units'] = product_ids[e]['close_stock'] * precision
                product_ids[e]['damaged'] = 0
                product_ids[e]['returned'] = 0
                product_ids[e]['amount_discount'] = 0

            else:
                product_ids[e] = {
                    'product_id': e,
                    'product_category_id': product.categ_id.id,
                    'sum_sale_chanel': 0,
                    'sum_fp_chanel': 0,
                    'sum_grab_chanel': 0,
                    'sum_shopee_chanel': 0,
                    'sum_lazmall_chanel': 0,
                    'sum_pos_chanel': 0,
                    'sum_pandamart_chanel': 0,
                    'amount_sale_cod': 0,
                    'amount_sale_ol': 0,
                    'amount_fp_cod': 0,
                    'amount_fp_ol': 0,
                    'amount_shopee_cod': 0,
                    'amount_shopee_ol': 0,
                    'amount_pos_cod': 0,
                    'amount_pos_ol': 0,
                    'amount_lazmall_cod': 0,
                    'amount_lazmall_ol': 0,
                    'amount_pandamart_cod': 0,
                    'amount_pandamart_ol': 0,
                    'amount_grab_cod': 0,
                    'amount_grab_ol': 0,
                    'open_stock': qty_previous_day[e]['qty_available'],
                    'close_stock': qty_today[e]['qty_available'],
                    'open_stock_units': qty_previous_day[e]['qty_available'] * precision,
                    'close_stock_units': qty_today[e]['qty_available'] * precision,
                    'damaged': 0,
                    'returned': 0,
                    'amount_discount': 0,
                    'asc_delivery': 0
                }

        for sale_order in sale_orders:
            # handle discount
            product_ids[discount_product.id][
                'amount_discount'] += abs(sale_order.computed_discount_total)
            # handle information of product
            for sale_order_line in sale_order.order_line:
                if sale_order_line.product_id.id in product_ids:
                    if not sale_order_line.is_reward_line and not sale_order_line.is_delivery and not sale_order_line.product_id.is_discount_product:
                        # handle amount and quantity
                        discount = sale_order.computed_discount_total * sale_order_line.price_subtotal / sale_order.amount_untaxed
                        if sale_order.team_id.id == sale:
                            product_ids[sale_order_line.product_id.id][
                                'sum_sale_chanel'] += sale_order_line.product_uom_qty
                            if sale_order.payment_method == 'cod':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_sale_cod'] += (sale_order_line.price_subtotal - discount)
                            elif sale_order.payment_method == 'online_payment':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_sale_ol'] += (sale_order_line.price_subtotal - discount)
                        elif sale_order.team_id.id == food_panda:
                            product_ids[sale_order_line.product_id.id][
                                'sum_fp_chanel'] += sale_order_line.product_uom_qty
                            if sale_order.payment_method == 'cod':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_fp_cod'] += (sale_order_line.price_subtotal - discount)
                            elif sale_order.payment_method == 'online_payment':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_fp_ol'] += (sale_order_line.price_subtotal - discount)
                        elif sale_order.team_id.id == grab:
                            product_ids[sale_order_line.product_id.id][
                                'sum_grab_chanel'] += sale_order_line.product_uom_qty
                            if sale_order.payment_method == 'cod':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_grab_cod'] += (sale_order_line.price_subtotal - discount)
                            elif sale_order.payment_method == 'online_payment':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_grab_ol'] += (sale_order_line.price_subtotal - discount)
                        elif sale_order.team_id.id == shopee:
                            product_ids[sale_order_line.product_id.id][
                                'sum_shopee_chanel'] += sale_order_line.product_uom_qty
                            if sale_order.payment_method == 'cod':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_shopee_cod'] += (sale_order_line.price_subtotal - discount)
                            elif sale_order.payment_method == 'online_payment':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_shopee_ol'] += (sale_order_line.price_subtotal - discount)
                        elif sale_order.team_id.id == pos:
                            product_ids[sale_order_line.product_id.id][
                                'sum_pos_chanel'] += sale_order_line.product_uom_qty
                            if sale_order.payment_method == 'cod':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_pos_cod'] += (sale_order_line.price_subtotal - discount)
                            elif sale_order.payment_method == 'online_payment':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_pos_ol'] += (sale_order_line.price_subtotal - discount)
                        elif sale_order.team_id.id == lazmall:
                            product_ids[sale_order_line.product_id.id][
                                'sum_lazmall_chanel'] += sale_order_line.product_uom_qty
                            if sale_order.payment_method == 'cod':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_lazmall_cod'] += (sale_order_line.price_subtotal - discount)
                            elif sale_order.payment_method == 'online_payment':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_lazmall_ol'] += (sale_order_line.price_subtotal - discount)
                        elif sale_order.team_id.id == pandamart:
                            product_ids[sale_order_line.product_id.id][
                                'sum_pandamart_chanel'] += sale_order_line.product_uom_qty
                            if sale_order.payment_method == 'cod':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_pandamart_cod'] += (sale_order_line.price_subtotal - discount)
                            elif sale_order.payment_method == 'online_payment':
                                product_ids[sale_order_line.product_id.id][
                                    'amount_pandamart_ol'] += (sale_order_line.price_subtotal - discount)
                        product_ids[sale_order_line.product_id.id][
                            'amount_discount'] += discount

        # handle scrap
        scrap = self.env['stock.scrap'].search(
            [('date_scrap', '=', self.date_report), ('state', '=', 'done'), ('location_id', '=', self.location_id.id)])
        for e in scrap:
            product_ids[e.product_id.id]['damaged'] += e.scrap_qty

        # handle return
        return_picking = self.env['stock.picking'].search(
            [('date_return', '=', self.date_report), ('is_return_picking', '=', True), ('state', '=', 'done'),
             ('location_dest_id', '=', self.location_id.id)])
        for e in return_picking:
            for f in e.move_ids_without_package:
                if not f.scrapped:
                    product_ids[f.product_id.id]['returned'] += f.product_uom_qty

        # handle asc delivery
        if not self.location_id:
            asc_deliveries = self.env['stock.picking'].search(
                [('date_done', '>=', start_order_date), ('date_done', '<', end_order_date),
                 ('state', '=', 'done'), ('is_return_picking', '=', False), ('picking_type_id.code', '=', 'incoming')])
        else:
            asc_deliveries = self.env['stock.picking'].search(
                [('date_done', '>=', start_order_date), ('date_done', '<', end_order_date),
                 ('state', '=', 'done'), ('location_dest_id', '=', self.location_id.id),
                 ('is_return_picking', '=', False), ('picking_type_id.code', '=', 'incoming')])

        delivery_quantity = {}
        for delivery in asc_deliveries:
            for delivery_line in delivery.move_ids_without_package:
                if not delivery_line.scrapped:
                    if delivery_line.product_id.id in delivery_quantity:
                        delivery_quantity[delivery_line.product_id.id] += delivery_line.quantity_done
                    else:
                        delivery_quantity[delivery_line.product_id.id] = delivery_line.quantity_done

        for e in delivery_quantity:
            product_ids[e]['asc_delivery'] = delivery_quantity[e]

        self.env['sale.hnk.report.line'].search([]).unlink()

        for e in product_ids:
            values.append([0, 0, product_ids[e]])
        res = self.env['sale.hnk.report'].create({
            'date_report': self.date_report,
            'report_line_ids': values
        })

        self.env['sale.hnk.report'].search([('id', '!=', res.id)]).unlink()
        tree_view_id = self.env.ref('advanced_sale.sale_hnk_report_line_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree')],
            'view_mode': 'tree',
            'name': 'Sale & Stock Report',
            'res_model': 'sale.hnk.report.line',
            'domain': [('sale_report_id', '=', res.id)],
            'context': {'search_default_group_category_id': 1},
            'target': 'main'
        }
        return action


class SaleHnkReportLine(models.Model):
    _name = 'sale.hnk.report.line'

    product_id = fields.Many2one('product.product', string="Product")
    product_category_id = fields.Many2one('product.category', string="Product Category")
    open_stock = fields.Float("Opening Stock")
    open_stock_units = fields.Float(string="UNITS btls/cans (Opening)")

    damaged = fields.Float(string="Damaged(UNITS btls/cans)")
    returned = fields.Float(string="Return")

    sum_sale_chanel = fields.Float(string="Sold Drinkies")
    sum_fp_chanel = fields.Float(string="Sold FP")
    sum_grab_chanel = fields.Float(string="Sold Grab")
    sum_shopee_chanel = fields.Float(string="Sold Shopee")
    sum_pos_chanel = fields.Float(string="Sold POS")
    sum_lazmall_chanel = fields.Float(string="Sold Lazmall")
    sum_pandamart_chanel = fields.Float(string="Sold Pandamart")

    amount_sale_cod = fields.Float(string="Amount Drinkies COD")
    amount_sale_ol = fields.Float(string="Amount Drinkies Online")

    amount_fp_cod = fields.Float(string="Amount FP COD")
    amount_fp_ol = fields.Float(string="Amount FP Online")

    amount_grab_cod = fields.Float(string="Amount Grab COD")
    amount_grab_ol = fields.Float(string="Amount Grab Online")

    amount_shopee_cod = fields.Float(string="Amount Shopee COD")
    amount_shopee_ol = fields.Float(string="Amount Shopee Online")

    amount_pos_cod = fields.Float(string="Amount POS COD")
    amount_pos_ol = fields.Float(string="Amount POS Online")

    amount_lazmall_cod = fields.Float(string="Amount Lazmall COD")
    amount_lazmall_ol = fields.Float(string="Amount Lazmall Online")

    amount_pandamart_cod = fields.Float(string="Amount Pandamart COD")
    amount_pandamart_ol = fields.Float(string="Amount Pandamart Online")

    close_stock = fields.Float(string="Closing Stock")
    close_stock_units = fields.Float(string="UNITS btls/cans (Closing)")
    amount_discount = fields.Float(string="Amount Discount")
    sale_report_id = fields.Many2one('sale.hnk.report')
    asc_delivery = fields.Float(string="ASC Delivery")
