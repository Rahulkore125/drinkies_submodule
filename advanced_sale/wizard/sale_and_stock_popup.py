import datetime

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class SaleAndStockPopup(models.TransientModel):
    _name = "sale.and.stock.popup"

    compute_at_date = fields.Selection([
        (0, 'At a Specific Date'),
        (1, 'At a Time Period')
    ], string="Compute", default=0)

    # def _get_from_datetime(self):
    #     today_date = datetime.date.today()
    #     today_from = datetime.datetime(int(today_date.year), int(today_date.month), int(today_date.day), 0, 0, 0)
    #     print(str(today_from))
    #     return today_from
    #
    # def _get_to_datetime(self):
    #     today_date = datetime.date.today()
    #     today_to = datetime.datetime(int(today_date.year), int(today_date.month), int(today_date.day), 23, 59, 59)
    #     print(str(today_to))
    #     return today_to

    date_report = fields.Date(string="Date Report", default=fields.Date.today)
    from_date_report = fields.Datetime(string="From Date", default=datetime.datetime.now())
    to_date_report = fields.Datetime(string="To Date", default=datetime.datetime.now())
    product_test = fields.Many2one(comodel_name="product.product", string="Product")

    def generate_report(self):
        if self.compute_at_date == 0:
            date_report = self.date_report
            date_from = datetime.datetime(int(date_report.year), int(date_report.month), int(date_report.day), 0, 0, 0)
            date_to = datetime.datetime(int(date_report.year), int(date_report.month), int(date_report.day), 23, 59, 59)
            sale_orders = self.env['sale.order'].sudo().search(
                [('state', 'in', ['done', 'sale']), ('confirmation_date', '<=', date_to),
                 ('confirmation_date', '>=', date_from)])
            if sale_orders:
                self.env['sale.and.stock.report'].sudo().search([]).unlink()
                for order in sale_orders:
                    if order.order_line:
                        for line in order.order_line:
                            self.env['sale.and.stock.report'].create({
                                'product_id': line.product_id.id,
                                'location_id': line.order_id.location_id.id if line.order_id.location_id else False,
                                'team_id': line.order_id.team_id.id if line.order_id.team_id else False,
                                'payment_method': line.order_id.payment_method,
                                'sold': line.qty_invoiced,
                                'amount': line.price_subtotal,
                            })
        else:
            date_from = self.from_date_report
            date_to = self.to_date_report
            sale_orders = self.env['sale.order'].sudo().search(
                [('state', 'in', ['done', 'sale']), ('confirmation_date', '<=', date_to),
                 ('confirmation_date', '>=', date_from)])
            if sale_orders:
                self.env['sale.and.stock.report'].sudo().search([]).unlink()
                for order in sale_orders:
                    if order.order_line:
                        for line in order.order_line:
                            self.env['sale.and.stock.report'].create({
                                'product_id': line.product_id.id,
                                'location_id': line.order_id.location_id.id if line.order_id.location_id else False,
                                'team_id': line.order_id.team_id.id if line.order_id.team_id else False,
                                'payment_method': line.order_id.payment_method,
                                'sold': line.qty_invoiced,
                                'amount': line.price_subtotal,
                            })
        tree_view_id = self.env.ref('advanced_sale.sale_and_stock_report_view_tree').id
        action = {
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree')],
            'view_mode': 'tree',
            'name': 'Sale & Stock Report',
            'res_model': 'sale.and.stock.report',
            # 'context': {'search_default_group_category_id': 1},
            'target': 'main'
        }
        return action

    # def generate_report_test(self):
    #     date_from = self.from_date_report
    #     date_to = self.to_date_report
    #     res = self.product_test._compute_quantities_dict(
    #         self._context.get('lot_id'),
    #         self._context.get(
    #             'owner_id'),
    #         self._context.get(
    #             'package_id'),
    #         from_date=date_from,
    #         to_date=date_to)
    #     print(res)
