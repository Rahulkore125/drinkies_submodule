from datetime import datetime, date

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.tools import float_is_zero
from ...magento2_connector.utils.magento.rest import Client


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
    location_id = fields.Many2one('stock.location', domain="[('in_report', '=', True)]", track_visibility='onchange', string="Location")

    # owner location can see own SO, invoice
    user_related = fields.Many2one(string="Owner location", comodel_name="res.users", compute="compute_user_related",
                                   store=True)
    delivery_date = fields.Datetime(string='Delivery date', track_visibility='onchange')

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

    @api.multi
    def action_confirm_complete(self):
        for so in self:
            print(so.name)
            # find all product template manage multiple sku one stock
            # determine the remaining stock
            multiple_sku_tmpl = {}
            for line in so.order_line:
                if line.product_id.product_tmpl_id.multiple_sku_one_stock:
                    if line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                        multiple_sku_tmpl[line.product_id.product_tmpl_id.id] = \
                            multiple_sku_tmpl[
                                line.product_id.product_tmpl_id.id] - line.product_uom_qty * line.product_id.deduct_amount_parent_product
                    else:
                        variant_manage_stock = line.product_id.product_tmpl_id.variant_manage_stock
                        original_quantity = self.env['stock.quant'].search(
                            [('location_id', '=', so.location_id.id), ('product_id', '=', variant_manage_stock.id)])
                        multiple_sku_tmpl[
                            line.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product - line.product_uom_qty * line.product_id.deduct_amount_parent_product

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

                invoice.action_invoice_open()

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
            })
            if not so.sudo().delivery_date:
                so.sudo().write({
                    'delivery_date': datetime.now()
                })
            magento_so = self.env['magento.sale.order'].sudo().search([('odoo_id', '=', so.id)])
            magento_so.sudo().write({
                'state': 'complete',
                'status': 'complete',
            })

            # update stock for variant of multiple sku one stock
            magento_backend = self.env['magento.backend'].search([], limit=1)
            client = Client(magento_backend.web_url, magento_backend.access_token, True)
            if len(multiple_sku_tmpl) > 0:
                stock2magento = self.env['stock.to.magento']
                stock2magento.force_update_inventory_special_keg(location_id=so.location_id,
                                                                 location_dest_id=False,
                                                                 multiple_sku_tmpl=multiple_sku_tmpl, client=client,
                                                                 type='outgoing')

            # sync stock to magagento
            # stock2magento.sync_quantity_to_magento(location_id=self.location_id,
            #                                        product_id=line.product_id, client=client)

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

    @api.multi
    def action_invoice_create(self, grouped=False, final=False):
        """
        Create the invoice associated to the SO.
        :param grouped: if True, invoices are grouped by SO id. If False, invoices are grouped by
                        (partner_invoice_id, currency)
        :param final: if True, refunds will be generated if necessary
        :returns: list of created invoices
        """
        inv_obj = self.env['account.invoice']
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        invoices = {}
        references = {}
        invoices_origin = {}
        invoices_name = {}

        # Keep track of the sequences of the lines
        # To keep lines under their section
        inv_line_sequence = 0
        for order in self:
            group_key = order.id if grouped else (order.partner_invoice_id.id, order.currency_id.id)

            # We only want to create sections that have at least one invoiceable line
            pending_section = None

            # Create lines in batch to avoid performance problems
            line_vals_list = []
            # sequence is the natural order of order_lines
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    continue
                if group_key not in invoices:
                    inv_data = order._prepare_invoice()
                    invoice = inv_obj.create(inv_data)
                    references[invoice] = order
                    invoices[group_key] = invoice
                    invoices_origin[group_key] = [invoice.origin]
                    invoices_name[group_key] = [invoice.name]
                elif group_key in invoices:
                    if order.name not in invoices_origin[group_key]:
                        invoices_origin[group_key].append(order.name)
                    if order.client_order_ref and order.client_order_ref not in invoices_name[group_key]:
                        invoices_name[group_key].append(order.client_order_ref)

                if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final):
                    if pending_section:
                        section_invoice = pending_section.invoice_line_create_vals(
                            invoices[group_key].id,
                            pending_section.qty_to_invoice
                        )
                        inv_line_sequence += 1
                        section_invoice[0]['sequence'] = inv_line_sequence
                        line_vals_list.extend(section_invoice)
                        pending_section = None

                    inv_line_sequence += 1
                    inv_line = line.invoice_line_create_vals(
                        invoices[group_key].id, line.qty_to_invoice
                    )
                    inv_line[0]['sequence'] = inv_line_sequence
                    line_vals_list.extend(inv_line)

            if references.get(invoices.get(group_key)):
                if order not in references[invoices[group_key]]:
                    references[invoices[group_key]] |= order

            self.env['account.invoice.line'].create(line_vals_list)

        for group_key in invoices:
            invoices[group_key].write({'name': ', '.join(invoices_name[group_key]),
                                       'origin': ', '.join(invoices_origin[group_key])})
            sale_orders = references[invoices[group_key]]
            if len(sale_orders) == 1:
                invoices[group_key].reference = sale_orders.reference

        # if not invoices:
        #     raise UserError(_('There is no invoiceable line. If a product has a Delivered quantities invoicing policy, please make sure that a quantity has been delivered.'))

        for invoice in invoices.values():
            invoice.compute_taxes()
            # if not invoice.invoice_line_ids:
            #     raise UserError(_('There is no invoiceable line. If a product has a Delivered quantities invoicing policy, please make sure that a quantity has been delivered.'))
            # If invoice is negative, do a refund invoice instead
            if invoice.amount_total < 0:
                invoice.type = 'out_refund'
                for line in invoice.invoice_line_ids:
                    line.quantity = -line.quantity
            # Use additional field helper function (for account extensions)
            for line in invoice.invoice_line_ids:
                line._set_additional_fields(invoice)
            # Necessary to force computation of taxes. In account_invoice, they are triggered
            # by onchanges, which are not triggered when doing a create.
            invoice.compute_taxes()
            # Idem for partner
            so_payment_term_id = invoice.payment_term_id.id
            fp_invoice = invoice.fiscal_position_id
            invoice._onchange_partner_id()
            invoice.fiscal_position_id = fp_invoice
            # To keep the payment terms set on the SO
            invoice.payment_term_id = so_payment_term_id
            invoice.message_post_with_view('mail.message_origin_link',
                                           values={'self': invoice, 'origin': references[invoice]},
                                           subtype_id=self.env.ref('mail.mt_note').id)
        return [inv.id for inv in invoices.values()]


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount = fields.Float(string='Discount (%)', digits=dp.get_precision('Discount'), default=0.0)

    @api.onchange('product_id')
    def onchange_unit_price(self):
        if self.product_id.id and not self.order_id.partner_id:
            self.price_unit = self.product_id.lst_price

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
    location_id = fields.Many2one('stock.location', domain="[('in_report', '=', True)]",
                                  string="Location")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['location_id'] = ', s.location_id as location_id'
        fields['warehouse_id'] = ', s.warehouse_id as warehouse_id'

        groupby += """, s.location_id
           , s.warehouse_id
           """

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)

    # def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
    #     with_ = ("WITH %s" % with_clause) if with_clause else ""
    #
    #     select_ = """
    #                 min(l.id) as id,
    #                 l.product_id as product_id,
    #                 t.uom_id as product_uom,
    #                 sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
    #                 sum(l.qty_delivered / u.factor * u2.factor) as qty_delivered,
    #                 sum(l.qty_invoiced / u.factor * u2.factor) as qty_invoiced,
    #                 sum(l.qty_to_invoice / u.factor * u2.factor) as qty_to_invoice,
    #                 sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_total,
    #                 sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as price_subtotal,
    #                 sum(l.untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_to_invoice,
    #                 sum(l.untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) as untaxed_amount_invoiced,
    #                 count(*) as nbr,
    #                 s.name as name,
    #                 s.date_order as date,
    #                 s.confirmation_date as confirmation_date,
    #                 s.state as state,
    #                 s.partner_id as partner_id,
    #                 s.user_id as user_id,
    #                 s.company_id as company_id,
    #                 extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
    #                 t.categ_id as categ_id,
    #                 s.pricelist_id as pricelist_id,
    #                 s.analytic_account_id as analytic_account_id,
    #                 s.team_id as team_id,
    #                 p.product_tmpl_id,
    #                 partner.country_id as country_id,
    #                 partner.commercial_partner_id as commercial_partner_id,
    #                 sum(p.weight * l.product_uom_qty / u.factor * u2.factor) as weight,
    #                 sum(p.volume * l.product_uom_qty / u.factor * u2.factor) as volume,
    #                 s.id as order_id,
    #                 l.discount as discount,
    #                 DATE_PART('day', s.confirmation_date::timestamp - s.create_date::timestamp) as days_to_confirm,
    #                 s.invoice_status as invoice_status
    #             """
    #
    #     for field in fields.values():
    #         select_ += field
    #
    #     from_ = """
    #                     sale_order_line l
    #                           join sale_order s on (l.order_id=s.id)
    #                           join res_partner partner on s.partner_id = partner.id
    #                             left join product_product p on (l.product_id=p.id)
    #                                 left join product_template t on (p.product_tmpl_id=t.id)
    #                         left join uom_uom u on (u.id=l.product_uom)
    #                         left join uom_uom u2 on (u2.id=t.uom_id)
    #                         left join product_pricelist pp on (s.pricelist_id = pp.id)
    #                     %s
    #             """ % from_clause
    #
    #     groupby_ = """
    #                 l.product_id,
    #                 l.order_id,
    #                 t.uom_id,
    #                 t.categ_id,
    #                 s.name,
    #                 s.date_order,
    #                 s.confirmation_date,
    #                 s.partner_id,
    #                 s.user_id,
    #                 s.state,
    #                 s.company_id,
    #                 s.pricelist_id,
    #                 s.analytic_account_id,
    #                 s.team_id,
    #                 p.product_tmpl_id,
    #                 partner.country_id,
    #                 partner.commercial_partner_id,
    #                 s.id %s,
    #                 l.discount,
    #                 s.invoice_status,
    #                 s.warehouse_id,
    #                 s.location_id
    #             """ % (groupby)
    #
    #     return '%s (SELECT %s FROM %s WHERE l.product_id IS NOT NULL GROUP BY %s)' % (with_, select_, from_, groupby_)
    #
    # @api.model_cr
    # def init(self):
    #     # self._table = sale_report
    #     fields = {
    #         'value2': ', s.computed_discount_total/s.number_of_sale_order_line as discount_amount'
    #     }
    #
    #     tools.drop_view_if_exists(self.env.cr, self._table)
    #     self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query(fields=fields)))
