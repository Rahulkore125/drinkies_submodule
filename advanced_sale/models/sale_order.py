from odoo import models, fields, api
from odoo import tools
from odoo.addons import decimal_precision as dp
from datetime import datetime, date
from ...magento2_connector.utils.magento.rest import Client
from odoo import tools, _
from odoo.exceptions import UserError
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    estimate_discount_total = fields.Monetary(string='Additional Whole Order Discount')
    computed_discount_total = fields.Monetary(string='Discount Amount', compute='compute_discount_total', store=True)
    payment_method = fields.Selection(string="Payment Method",
                                      selection=[('cod', 'COD'), ('online_payment', 'Online Payment'), ],
                                      required=False, default="cod")
    date_confirm_order = fields.Date()
    number_of_sale_order_line = fields.Integer(compute='_compute_number_order_line', store=True)
    shipper = fields.Many2one('shipper', string="Shipper")
    has_a_delivery = fields.Boolean(
        compute='_compute_has_a_delivery', string='Has delivery',
        help="Has an order line set for delivery", store=True)

    currency_id = fields.Many2one('res.currency', readonly=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    location_id = fields.Many2one('stock.location', string="Location", domain=[('is_from_magento', '=', True)])

    # owner location can see own SO, invoice
    user_related = fields.Many2one(string="Owner location", comodel_name="res.users", compute="compute_user_related",
                                   store=True)
    delivery_date = fields.Datetime(string='Delivery date')

    @api.depends('location_id')
    def compute_user_related(self):
        for rec in self:
            rec.user_related = False
            if rec.location_id:
                if rec.location_id.partner_id:
                    user_related = self.env['res.users'].sudo().search(
                        [('partner_id', '=', rec.location_id.partner_id.id)], limit=1)
                    if user_related:
                        rec.user_related = user_related

    @api.depends('picking_ids')
    def _compute_has_a_delivery(self):
        for order in self:
            # order.has_a_delivery = any(order.order_line.filtered('is_delivery'))
            if len(order.picking_ids) > 0:
                order.has_a_delivery = True
            else:
                order.has_a_delivery = False

    @api.multi
    @api.depends('order_line')
    def _compute_number_order_line(self):
        for rec in self:
            rec.number_of_sale_order_line = len(rec.order_line)

    @api.model
    def create(self, vals_list):
        res = super(SaleOrder, self).create(vals_list)
        return res

    @api.multi
    def action_confirm_complete(self):
        for so in self:
            # for e in so.order_line:
                # if e.product_id.product_tmpl_id.multiple_sku_one_stock:
                #     stock_quant = so.env['stock.quant'].search(
                #         [('location_id', '=', so.location_id.id),
                #          ('product_id', '=', e.product_id.product_tmpl_id.variant_manage_stock.id)])
                #
                #     stock_quant.sudo().write({
                #         'updated_qty': True,
                #         'original_qty': stock_quant.original_qty - e.product_uom_qty * e.product_id.deduct_amount_parent_product
                #     })

            stock_pickings = so.env['stock.picking'].search(
                [('sale_id', '=', so.id), ('picking_type_id.code', '=', 'outgoing')])

            for stock_picking in stock_pickings:
                for move_line in stock_picking.move_lines:
                    move_line.quantity_done = move_line.product_uom_qty

                for move_line_id in stock_picking.move_line_ids:
                    if so.location_id.id:
                        move_line_id.location_id = so.location_id.id
                stock_picking.location_id = so.location_id.id
                stock_picking.action_done()
                stock_picking.date_done_delivery = date.today()

            so.date_confirm_order = date.today()
            invoice_id = so.action_invoice_create(grouped=False, final=False)

            for e in invoice_id:
                invoice = self.env['account.invoice'].browse(e)
                invoice.update({
                    'original_invoice': True,
                    'order_id': so.id
                })
                # print('ste_' + rec.magento_bind_ids.state)
                invoice.action_invoice_open()
                # if rec.is_magento_sale_order and rec.magento_bind_ids.state != 'complete':
                #     print('not_done')
                #     return result
                # else:
                if invoice.state != 'open':
                    invoice.state = 'open'
                journal_id = 'cod'
                if so.payment_method == 'cod':
                    journal_id = self.env['account.journal'].search([('code', '=', 'CSH1')]).id
                elif so.payment_method == 'online_payment':
                    journal_id = self.env['account.journal'].search([('code', '=', 'BNK1')]).id
                payment = self.env['account.payment'].create({
                    'invoice_ids': [(4, e, None)],
                    'amount': invoice.amount_total,
                    'payment_date': date.today(),
                    'communication': invoice.number,
                    'payment_type': 'inbound',
                    'journal_id': journal_id,
                    'partner_type': 'customer',
                    'payment_method_id': 1,
                    'partner_id': invoice.partner_id.id
                })
                payment.action_validate_invoice_payment()
            so.sudo().write({
                'state': 'done',
                'delivery_date': datetime.now()
            })
            magento_so = self.env['magento.sale.order'].sudo().search([('odoo_id', '=', so.id)])
            magento_so.sudo().write({
                'state': 'complete',
                'status': 'complete',
            })
            for line in so.order_line:
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

    @api.depends('computed_discount_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        discount_product = self.env.ref('magento2_connector.discount_record').id

        for order in self:
            amount_untaxed = amount_tax = 0.0
            amount_reward = 0.0
            for line in order.order_line:
                if not line.is_reward_line and not line.product_id.id == discount_product:
                    amount_untaxed += line.price_subtotal
                else:
                    amount_reward += line.price_subtotal
                amount_tax += line.price_tax

            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax - order.computed_discount_total
            })


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    # @api.multi
    # @api.depends('order_id.estimate_discount_total')
    # def _compute_discount_order_line(self):
    #     for rec in self:
    #         sum = 0
    #         for e in rec.order_id.order_line:
    #             if not e.is_reward_line and not e.is_delivery:
    #                 sum += e.price_subtotal
    #         if sum > 0:
    #             each_line_order_discount = rec.order_id.computed_discount_total / sum * 100
    #             for e in rec.order_id.order_line:
    #                 if not e.is_reward_line and not e.is_delivery:
    #                     e.discount = each_line_order_discount

    @api.onchange('product_id')
    def onchange_unit_price(self):
        if self.product_id.id and not self.order_id.partner_id:
            self.price_unit = self.product_id.list_price

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'qty_delivered')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                            product=line.product_id, partner=line.order_id.partner_shipping_id)

            # if not line.order_id.has_delivery:
            if not line.order_id.has_a_delivery:
                line.update({
                    'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'price_total': taxes['total_included'],
                    'price_subtotal': taxes['total_excluded'],
                })
            else:
                if line.is_delivery or line.is_reward_line:
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })
                elif line.product_id.type == 'service':
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': taxes['total_excluded'],
                    })
                else:
                    line.update({
                        'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'price_total': taxes['total_included'],
                        'price_subtotal': line.price_unit * line.product_uom_qty
                    })


class SaleReport(models.Model):
    _inherit = 'sale.report'

    # total_discount = fields.Float("Total Discount")

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
                    min(l.id) as id,
                    l.product_id as product_id,
                    t.uom_id as product_uom,
                    sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
                    sum(l.qty_delivered / u.factor * u2.factor) as qty_delivered,
                    sum(l.qty_invoiced / u.factor * u2.factor) as qty_invoiced,
                    sum(l.qty_to_invoice / u.factor * u2.factor) as qty_to_invoice,
                    sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_total,
                    sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_subtotal,
                    sum(l.untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_to_invoice,
                    sum(l.untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_invoiced,
                    count(*) as nbr,
                    s.name as name,
                    s.date_order as date,
                    s.confirmation_date as confirmation_date,
                    s.state as state,
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.analytic_account_id as analytic_account_id,
                    s.team_id as team_id,
                    p.product_tmpl_id,
                    partner.country_id as country_id,
                    partner.commercial_partner_id as commercial_partner_id,
                    sum(p.weight * l.product_uom_qty / u.factor * u2.factor) as weight,
                    sum(p.volume * l.product_uom_qty / u.factor * u2.factor) as volume,
                    s.id as order_id,
                    l.discount as discount,
                    DATE_PART('day', s.confirmation_date::timestamp - s.create_date::timestamp) as days_to_confirm,
                    s.invoice_status as invoice_status
                """

        for field in fields.values():
            select_ += field

        from_ = """
                        sale_order_line l
                              join sale_order s on (l.order_id=s.id)
                              join res_partner partner on s.partner_id = partner.id
                                left join product_product p on (l.product_id=p.id)
                                    left join product_template t on (p.product_tmpl_id=t.id)
                            left join uom_uom u on (u.id=l.product_uom)
                            left join uom_uom u2 on (u2.id=t.uom_id)
                            left join product_pricelist pp on (s.pricelist_id = pp.id)
                        %s
                """ % from_clause

        groupby_ = """
                    l.product_id,
                    l.order_id,
                    t.uom_id,
                    t.categ_id,
                    s.name,
                    s.date_order,
                    s.confirmation_date,
                    s.partner_id,
                    s.user_id,
                    s.state,
                    s.company_id,
                    s.pricelist_id,
                    s.analytic_account_id,
                    s.team_id,
                    p.product_tmpl_id,
                    partner.country_id,
                    partner.commercial_partner_id,
                    s.id %s,
                    l.discount,
                    s.invoice_status
                """ % (groupby)

        return '%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)

    @api.model_cr
    def init(self):
        # self._table = sale_report
        fields = {
            'value2': ', s.computed_discount_total/s.number_of_sale_order_line as discount_amount'
        }

        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query(fields=fields)))
