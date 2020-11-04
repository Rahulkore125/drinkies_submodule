import datetime
import sys
import traceback
from datetime import date, datetime

import math

from odoo import models, fields, api
from odoo import tools, _
from odoo.exceptions import ValidationError, UserError
from ...utils.magento.customer import Customer, CustomerGroup
from ...utils.magento.location import Location
from ...utils.magento.product import Product
from ...utils.magento.rest import Client
from ...utils.magento.sales import Order

TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale',
    'in_refund': 'purchase',
}


def get_current_page(total_count, page_size):
    total_page = total_count / page_size
    if 0 < total_page < 1:
        total_page = 1
    else:
        total_page = math.ceil(total_page)
    return total_page


class MagentoBackend(models.Model):

    @api.model
    def _default_journal(self):
        if self._context.get('default_journal_id', False):
            return self.env['account.journal'].browse(self._context.get('default_journal_id'))
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', [TYPE2JOURNAL[ty] for ty in inv_types if ty in TYPE2JOURNAL]),
            ('company_id', '=', company_id),
        ]
        journal_with_currency = False
        if self._context.get('default_currency_id'):
            currency_clause = [('currency_id', '=', self._context.get('default_currency_id'))]
            journal_with_currency = self.env['account.journal'].search(domain + currency_clause, limit=1)
        return journal_with_currency or self.env['account.journal'].search(domain, limit=1)

    _name = "magento.backend"

    name = fields.Char(string='Name', required=True)
    version = fields.Selection(selection=([('Magento 2.3', '2.3'), ('Magento 2.2', '2.2')]), default='Magento 2.3',
                               string='Version', required=True)
    web_url = fields.Char(
        string='Url',
        required=True,
        help="Url to magento application",
    )
    access_token = fields.Char(string='Token', required=True, help="Access token to magento Integration")

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        readonly=True,
    )
    website_ids = fields.One2many('magento.website', 'backend_id', string='Website', readonly=True, )
    prefix_order = fields.Char('Prefix Order')
    # Page Size
    products_pageSize = fields.Integer(string='Products page size', required=True, default=500)

    customers_pageSize = fields.Integer(string='Customers page size', required=True, default=500)

    sale_orders_pageSize = fields.Integer(string='Sale oders page size', required=True, default=500)

    invoice_pageSize = fields.Integer(string='Invoice page size', required=True, default=500)

    # auto fetch
    auto_import_magento = fields.Boolean(string='Import Automatic', default=False)
    interval_number_import_magento = fields.Integer(string='Execute every', default=5)
    interval_type_import_magento = fields.Selection([('minutes', 'Minutes'),
                                                     ('hours', 'Hours'),
                                                     ('days', 'Days'),
                                                     ('weeks', 'Weeks'),
                                                     ('months', 'Months')], string='Interval Unit', default='months')
    nextcall_import_magento = fields.Datetime(string='Next execution date')
    auto_fetching = fields.Boolean(string='Fetching', default=False)

    _sql_constraints = [('uniq_web_url', 'unique(web_url)', "The Url must be unique !")]

    @api.constrains('interval_number_import_magento')
    def _contrains_interval_number_import_magento(self):
        if self.interval_number_import_magento <= 0:
            raise ValidationError("Time excute must be greater than 0")
        if type(self.interval_number_import_magento) == float:
            raise ValidationError("time excute very must be integer not float")

    @api.model
    def create(self, values):
        record = super(MagentoBackend, self).create(values)
        if values.get('web_url') and values.get('access_token'):
            access_token = values.get('access_token')
            url = values.get('web_url')
            self.pull_magento_backend(url, access_token, record.id)

        if values.get('auto_import_magento'):
            self._ir_cron(values.get('auto_import_magento'), values.get('interval_number_import_magento'),
                          values.get('interval_type_import_magento'), values.get('nextcall_import_magento'),
                          'ir_cron_pull_magento')
        return record

    @api.multi
    def write(self, values):
        # ir cron write
        interval_number_import_magento = values.get('interval_number_import_magento') if values.get(
            'interval_number_import_magento', False) else self.interval_number_import_magento
        interval_type_import_magento = values.get('interval_type_import_magento') if values.get(
            'interval_type_import_magento', False) else self.interval_type_import_magento
        nextcall_import_magento = values.get('nextcall_import_magento') if values.get('nextcall_import_magento',
                                                                                      False) else self.nextcall_import_magento
        # auto_import_magento = values.get('auto_import_magento') if values.get('auto_import_magento',
        #                                                                           False) else self.auto_import_magento
        if 'auto_import_magento' in values:
            auto_import_magento = values.get('auto_import_magento')
            self._ir_cron(auto_import_magento, interval_number_import_magento, interval_type_import_magento,
                          nextcall_import_magento, 'ir_cron_pull_magento')
        return super(MagentoBackend, self).write(values)

    @api.multi
    def unlink(self):
        self.env.cr.execute(""" DELETE FROM magento_res_partner_category WHERE TRUE;
                                DELETE FROM magento_address WHERE TRUE;
                                DELETE FROM magento_res_partner WHERE TRUE;
                                DELETE FROM res_partner WHERE is_from_magento = TRUE;
                                DELETE FROM magento_website WHERE TRUE;
                                DELETE FROM magento_pull_history WHERE TRUE;
                                DELETE FROM magento_sale_order WHERE TRUE;
                                DELETE FROM sale_order WHERE TRUE;
                                DELETE FROM magento_account_invoice WHERE TRUE;
                                DELETE FROM magento_backend WHERE TRUE;
                                DELETE FROM magento_account_invoice WHERE TRUE;
                                DELETE FROM res_partner WHERE id > 50;
                                DELETE FROM magento_storeview WHERE TRUE;
                                DELETE FROM magento_store WHERE TRUE;
                                DELETE FROM res_partner_category WHERE TRUE;""")

    def _ir_cron(self, auto_import, interval_number, interval_type, nextcall, id):
        if auto_import:
            self.env.ref('magento2_connector.' + str(id)).write({
                'interval_number': interval_number,
                'interval_type': interval_type,
                'nextcall': nextcall,
                'numbercall': -1,
                'priority': 1,
                'active': True
            })
        else:
            self.env.ref('magento2_connector.' + str(id)).write({
                'numbercall': 0,
                'active': False,
            })

    def pull_magento_backend(self, url, access_token, backend_id):
        # try:
        if 'https' in url:
            client = Client(url, access_token, True)
        else:
            client = Client(url, access_token, False)
        # website
        websites = client.call('rest/V1/store/websites', '')

        website_magento_id = []
        website_odoo_id = []
        check_len_arr = False
        for website in websites:
            self.env.cr.execute("""INSERT INTO magento_website (name, code,backend_id,external_id,create_date, write_date,create_uid,write_uid)
                                        VALUES (%s, %s, %s, %s, %s ,%s, %s, %s) ON CONFLICT (backend_id, external_id) DO UPDATE SET (name,code)=(EXCLUDED.name,EXCLUDED.code) RETURNING id""",
                                (website['name'], website['code'], backend_id, website['id'],
                                 datetime.today(), datetime.today(), self.env.uid, self.env.uid))
            web_id = self.env.cr.fetchall()[0][0]
            website_magento_id.append(website['id'])
            website_odoo_id.append(web_id)

        if len(website_odoo_id) == len(website_magento_id):
            check_len_arr = True

        # store
        store_groups = client.call('rest/V1/store/storeGroups', '')
        for store_group in store_groups:
            self.env.cr.execute("""INSERT INTO magento_store (name, code, root_category_id, website_id, backend_id, external_id)
                                       VALUES (%s, %s, %s, %s, %s, %s ) ON CONFLICT (backend_id, external_id) DO UPDATE SET (name, code, root_category_id, website_id) = (EXCLUDED.name, EXCLUDED.code, EXCLUDED.root_category_id, EXCLUDED.website_id)""",
                                (store_group['name'], store_group['code'] if 'code' in store_group else '',
                                 store_group['root_category_id'], website_odoo_id[
                                     website_magento_id.index(store_group['website_id'])] if check_len_arr else -1,
                                 backend_id, store_group['id']))
        # store view
        store_views = client.call('/rest/V1/store/storeViews', '')
        for store_view in store_views:
            self.env.cr.execute("""INSERT INTO magento_storeview (name,code,store_id,website_id,is_active,backend_id, external_id)
                                                       VALUES (%s, %s, %s, %s, %s, %s, %s ) ON CONFLICT (backend_id, external_id) DO UPDATE SET (name, code, store_id, website_id, is_active) =(EXCLUDED.name, EXCLUDED.code, EXCLUDED.store_id, EXCLUDED.website_id, EXCLUDED.is_active)  """,
                                (store_view['name'], store_view['code'] if 'code' in store_view else '',
                                 client.adapter_magento_id('magento_store', backend_id,
                                                           store_view['store_group_id'], self),
                                 website_odoo_id[
                                     website_magento_id.index(store_view['website_id'])] if check_len_arr else -1,
                                 store_view['is_active'] if 'is_active' in store_view else 1, backend_id,
                                 store_view['id']))

    def fetch_customers(self):
        if not self.auto_fetching:
            # get from config
            if not self.id:
                self = self.env['magento.backend'].search([], limit=1)
            backend_id = self.id
            url = self.web_url
            token = self.access_token
            self.pull_magento_backend(url, token, backend_id)

            page_size = self.customers_pageSize
            cus = Customer(url, token, True)

            if page_size > 0:
                current_page = 0
                pull_history = self.env['magento.pull.history'].search(
                    [('backend_id', '=', backend_id), ('name', '=', 'customers')])

                if pull_history:
                    # second pull
                    sync_date = pull_history.sync_date
                    customers = cus.list_gt_updated_at(sync_date)
                    if len(customers['items']) > 0:
                        pull_history.write({
                            'sync_date': datetime.today()
                        })

                else:
                    # first pull
                    self.env['magento.pull.history'].create({
                        'name': 'customers',
                        'sync_date': datetime.today(),
                        'backend_id': backend_id
                    })
                    customers = cus.list(page_size, current_page)

                cus_group = CustomerGroup(url, token, True)
                customer_groups = cus_group.list_all()
                cus_group.insert(customer_groups, url, token, backend_id, self)

                total_amount = customers['total_count']
                cus.insert(customers['items'], backend_id, url, token, self)
                total_page = total_amount / page_size

                if 0 < total_page < 1:
                    total_page = 1
                else:
                    total_page = math.ceil(total_page)

                for page in range(1, total_page):
                    customers = cus.list(page_size, page + 1)
                    cus.insert(customers['items'], backend_id, url, token, self)
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Fetch customers successful"
                },
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Customers are fetching by schedule action, you can fetch customers manually after schedule action finish"
                },
            }

    def fetch_products(self):
        if not self.auto_fetching:
            if not self.id:
                self = self.env['magento.backend'].search([], limit=1)
            backend_id = self.id
            url = self.web_url
            token = self.access_token

            pro = Product(url, token, True)

            page_size = self.products_pageSize

            if page_size > 0:
                current_page = 0
                if self:
                    pull_history_configurable_product = self.env['magento.pull.history'].search(
                        [('backend_id', '=', backend_id), ('name', '=', 'configurable_product')])
                    # Configurbale Product
                    try:
                        if pull_history_configurable_product:
                            # second pull
                            sync_date = pull_history_configurable_product.sync_date
                            products = pro.list_gt_updated_product(sync_date, 'eq')
                            if len(products['items']) > 0:
                                pull_history_configurable_product.write({
                                    'sync_date': datetime.today()
                                })

                        else:
                            # first pull
                            self.env['magento.pull.history'].create({
                                'name': 'configurable_product',
                                'sync_date': datetime.today(),
                                'backend_id': backend_id
                            })
                            products = pro.list_product(page_size, current_page, 'configurable', 'eq')
                        total_count = products['total_count']
                        # truong hop dac biet voi drinkies it san pham nen ko can chia thanh tung phan de fetch nua

                        pro.insert_configurable_product(products['items'], backend_id, url, token, self)

                        # total_page = get_current_page(total_count, page_size)
                        # if total_page > 0:
                        #     for page in range(1, total_page):
                        #         products = pro.list_product(page_size, page + 1, 'configurable', 'eq')
                        #         pro.insert_configurable_product(products['items'], backend_id, url, token)
                    except Exception as e:
                        traceback.print_exc(None, sys.stderr)
                        self.env.cr.execute("""INSERT INTO trace_back_information (time_log, infor)
                                                               VALUES (%s, %s)""",
                                            (datetime.now(), str(traceback.format_exc())))
                        self.env.cr.commit()
                        raise UserError(_('fetch product configurable %s or fetch product attribute') % tools.ustr(e))

                    # Normal Product
                    pull_history_normal_product = self.env['magento.pull.history'].search(
                        [('backend_id', '=', backend_id), ('name', '=', 'normal_product')])
                    try:
                        if pull_history_normal_product:
                            sync_date = pull_history_normal_product.sync_date
                            products = pro.list_gt_updated_product(sync_date, 'neq')
                            if len(products['items']) > 0:
                                pull_history_normal_product.write({
                                    'sync_date': datetime.today()
                                })
                        else:
                            # first pull
                            self.env['magento.pull.history'].create({
                                'name': 'normal_product',
                                'sync_date': datetime.today(),
                                'backend_id': backend_id
                            })
                            products = pro.list_product(page_size, current_page, 'configurable', 'neq')

                        # todo
                        # truong hop dac biet voi drinkies it san pham nen ko can chia thanh tung phan de fetch nua

                        total_count = products['total_count']
                        pro.insert_not_configurable_product(products['items'], backend_id, url, token, self)
                    except Exception as e:
                        traceback.print_exc(None, sys.stderr)
                        self.env.cr.execute("""INSERT INTO trace_back_information (time_log, infor)
                                                               VALUES (%s, %s)""",
                                            (datetime.now(), str(traceback.format_exc())))
                        self.env.cr.commit()

            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Fetch products successful"
                },
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Products are fetching by schedule action, you can fetch product manually after schedule action finish"
                },
            }

    def fetch_sale_orders(self):
        if not self.auto_fetching:
            if not self.id:
                self = self.env['magento.backend'].search([], limit=1)
            self.fetch_source()
            self.fetch_products()
            self.fetch_customers()
            self.fetch_tax()
            self.fetch_order_update()
            # self.fetch_invoice()

            backend_name = self.name
            backend_id = int(self.id)

            if not backend_id:
                first_backend = self.env['magento.backend'].search([], limit=1)
                if first_backend.id:
                    backend_id = first_backend.id
            url = self.web_url
            token = self.access_token
            prefix_order = self.prefix_order
            if prefix_order:
                prefix_order = prefix_order + '/'
            else:
                prefix_order = 'SO/Magento' + str(backend_id) + '/'

            page_size = self.sale_orders_pageSize
            order = Order(url, token, True)
            if page_size > 0:
                current_page = 0
                pull_history = self.env['magento.pull.history'].search(
                    [('backend_id', '=', backend_id), ('name', '=', 'sale_orders')])

                if pull_history:
                    # second pull
                    orders = []
                    sync_date = pull_history.sync_date
                    time_pull = datetime(sync_date.year, month=sync_date.month,
                                         day=sync_date.day, hour=00, minute=00, second=00)
                    orders_pull = order.list_order_updated_at_after_sync(time_pull)

                    if len(orders_pull['items']) > 0:
                        for e in orders_pull['items']:
                            existed_order = self.env['magento.sale.order'].search(
                                [('external_id', '=', int(e['items'][0]['order_id']))])
                            if not len(existed_order) > 0:
                                orders.append(e)

                    pull_history.write({
                        'sync_date': datetime.today()
                    })
                else:
                    # first pull
                    self.env['magento.pull.history'].create({
                        'name': 'sale_orders',
                        'sync_date': datetime.today(),
                        'backend_id': backend_id
                    })
                    orders_pull = order.list(page_size, current_page)
                    orders = []
                    for e in orders_pull['items']:
                        orders.append(e)

                total_amount = len(orders)
                if total_amount > 0:
                    order.importer_sale(orders, backend_id, backend_name, prefix_order, context=self)
                    # total_page = total_amount / page_size

                    # if 0 < total_page < 1:
                    #     total_page = 1
                    # else:
                    #     total_page = math.ceil(total_page)
                    #
                    # for page in range(1, total_page):
                    #     orders = order.list(page_size, page + 1)
                    #     order.importer_sale(orders, backend_id, backend_name, prefix_order, context=self)

                # page_size = 10
                # # for page in range(1, total_page):
                # orders = order.list(page_size, 1)
                # order.importer_sale(orders['items'], backend_id, backend_name, prefix_order, context=self)
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Fetch sale orders successful"
                },
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Sale Orders are fetching by schedule action, you can fetch sale orders manually after schedule action finish"
                },
            }

    # disable in this version
    def fetch_tax(self):
        backend_id = self.id
        url = self.web_url
        token = self.access_token
        magento_backend_name = self.name

        client = Client(url, token, True)

        account_tax_group_id = 1
        account_tax_group = self.env['account.tax.group'].search([('name', '=', magento_backend_name)], limit=1)
        if account_tax_group:
            account_tax_group_id = account_tax_group.id
        else:
            res = self.env['account.tax.group'].create({
                'name': magento_backend_name,
                'sequence': 10
            })
            account_tax_group_id = res.id

        # website
        tax_rates = client.call('/rest/V1/taxRates/search', 'searchCriteria')
        account_taxs = []
        for tax_rate in tax_rates['items']:
            if tax_rate['rate'] != 0:
                account_taxs.append((tax_rate['code'], tax_rate['rate'], 'sale', 'percent', 1, 1, account_tax_group_id,
                                     True, tax_rate['id'], backend_id))

        if account_taxs and len(account_taxs) > 0:
            self.env.cr.execute(
                """INSERT INTO account_tax (name, amount, type_tax_use, amount_type,company_id,sequence,tax_group_id, active, external_id, backend_id) VALUES {values} ON CONFLICT(external_id, backend_id) DO UPDATE SET (name, amount, active) = (EXCLUDED.name, EXCLUDED.amount, EXCLUDED.active) """
                    .format(values=", ".join(["%s"] * len(account_taxs))), tuple(account_taxs))
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'popup.dialog',
            'target': 'new',
            'context': {
                'default_message': "Fetch tax successful"
            },
        }

    def fetch_order_update(self):
        url = self.web_url
        token = self.access_token
        order = Order(url, token, True)
        backend_id = self.id
        # payment_journal = self.payment_journal.id
        pull_history = self.env['magento.pull.history'].search(
            [('backend_id', '=', backend_id), ('name', '=', 'sale_orders')])
        if pull_history:
            time_pull = datetime(pull_history.sync_date.year, month=pull_history.sync_date.month,
                                 day=pull_history.sync_date.day, hour=00, minute=00, second=00)
            orders_updated = order.list_order_updated_at_after_sync(time_pull)

            # todo chua co xu ly truong hop cancel khi da complete
            for e in orders_updated['items']:
                exist_order = self.env['magento.sale.order'].search([('external_id', '=', e['entity_id'])])
                if len(exist_order) == 0:
                    pass
                else:
                    if e['state'] == 'complete' and exist_order.state in ['processing', 'shipping']:
                        if exist_order.odoo_id.state != 'done':
                            exist_order.odoo_id.action_confirm_complete()
                        else:
                            for stock_picking in exist_order.picking_ids:
                                if stock_picking.state != 'done':
                                    stock_picking.action_cancel()
                            for invoice in exist_order.invoice_ids:
                                if invoice.state == 'open':
                                    if exist_order.payment_method == 'cod':
                                        journal_id = self.env['account.journal'].search([('code', '=', 'CSH1')]).id
                                    elif exist_order.payment_method == 'online_payment':
                                        journal_id = self.env['account.journal'].search([('code', '=', 'BNK1')]).id
                                    payment = self.env['account.payment'].create({
                                        'invoice_ids': [(4, invoice.id, None)],
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
                            exist_order.write({
                                'state': 'complete',
                                'status': 'complete'
                            })
                            self.env.cr.execute(
                                """UPDATE sale_order SET state = %s WHERE id = %s""", ('done', exist_order.odoo_id.id))
                    elif e['state'] == 'canceled' and exist_order.state in ['processing', 'shipping'] and \
                            exist_order.picking_ids[0].state != 'done':
                        # self.fetch_shipments()
                        # self.fetch_invoice()
                        if exist_order.odoo_id.state != 'done':
                            # has_picking_state_done = False
                            # if exist_order.picking_ids:
                            #     for picking in exist_order.picking_ids:
                            #         if picking.state == 'done':
                            #             has_picking_state_done = True
                            # if not has_picking_state_done:
                            exist_order.odoo_id.action_cancel()
                            exist_order.write({
                                'state': 'canceled',
                                'status': 'canceled',
                            })
                    elif e['state'] == 'canceled' and exist_order.state in ['complete']:
                        # elif e['state'] == 'canceled':
                        for stock_picking in exist_order.picking_ids:
                            if stock_picking.state != 'done':
                                stock_picking.action_cancel()
                            elif stock_picking.state == 'done':
                                new_picking_id, pick_type_id = self.env['stock.return.picking'].with_context(
                                    active_model='stock.picking', active_id=stock_picking.id).create(
                                    {})._create_returns()

                                ctx = dict(self.env.context)

                                ctx.update({
                                    'search_default_picking_type_id': pick_type_id,
                                    'search_default_draft': False,
                                    'search_default_assigned': False,
                                    'search_default_confirmed': False,
                                    'search_default_ready': False,
                                    'search_default_late': False,
                                    'search_default_available': False,
                                })

                                picking = self.env['stock.picking'].search([('id', '=', new_picking_id)])

                                multiple_sku_tmpl = {}
                                for move_line in picking.move_line_ids_without_package:
                                    if move_line.product_id.product_tmpl_id.multiple_sku_one_stock:
                                        if move_line.product_id.product_tmpl_id.id in multiple_sku_tmpl:
                                            multiple_sku_tmpl[move_line.product_id.product_tmpl_id.id] = \
                                                multiple_sku_tmpl[
                                                    move_line.product_id.product_tmpl_id.id] + move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product
                                        else:
                                            variant_manage_stock = move_line.product_id.product_tmpl_id.variant_manage_stock
                                            original_quantity = self.env['stock.quant'].search(
                                                [('location_id', '=', picking.location_dest_id.id),
                                                 ('product_id', '=', variant_manage_stock.id)])
                                            multiple_sku_tmpl[
                                                move_line.product_id.product_tmpl_id.id] = original_quantity.quantity * variant_manage_stock.deduct_amount_parent_product + move_line.product_uom_qty * move_line.product_id.deduct_amount_parent_product

                                if 'order_source_code' in e['extension_attributes']:
                                    source = self.env['stock.location'].search(
                                        [('magento_source_code', '=',
                                          e['extension_attributes']['order_source_code'])])
                                else:
                                    source = []

                                for move_line in picking.move_lines:
                                    move_line.quantity_done = move_line.product_uom_qty

                                for move_line_id in picking.move_line_ids:
                                    if len(source) > 0:
                                        move_line_id.location_dest_id = source.id

                                picking.action_done()
                                picking.is_return_picking = True

                                picking.date_return = date.today()

                                origin_picking = self.env['stock.picking'].search(
                                    [('id', '=', stock_picking.id)])
                                origin_picking.has_return_picking = True

                                magento_backend = self.env['magento.backend'].search([], limit=1)
                                client = Client(magento_backend.web_url, magento_backend.access_token, True)

                                #update quantity multiple keg
                                if len(multiple_sku_tmpl) > 0:
                                    stock2magento = self.env['stock.to.magento']
                                    stock2magento.force_update_inventory_special_keg(
                                        location_id=picking.location_dest_id,
                                        location_dest_id=False,
                                        multiple_sku_tmpl=multiple_sku_tmpl, client=client,
                                        type='incoming')

                                ## after action_done(), sync stock to magento
                                stock2magento = self.env['stock.to.magento']
                                for line in picking.move_line_ids:
                                    stock2magento.sync_quantity_to_magento(location_id=picking.location_dest_id,
                                                                           product_id=line.product_id, client=client)
                        refund = self.env['account.invoice.refund'].create({
                            'filter_refund': 'refund',
                            'description': 'Return product',
                            'date_invoice': date.today(),
                        })
                        # refund.sudo().invoice_refund()
                        invoice = self.env['account.invoice'].search([('original_invoice', '=', True), (
                            'order_id', '=', exist_order.odoo_id.id)])
                        invoice_lines = invoice.invoice_line_ids

                        invoice_lines_update = []
                        invoice_lines_copy = {}
                        for e in invoice_lines:
                            invoice_copy = e.copy()
                            invoice_copy.write({'invoice_id': False})
                            invoice_copy.write({
                                'quantity': e.quantity
                            })
                            invoice_lines_update.append(invoice_copy.id)
                        # invoice_lines_update = []
                        # for e in self.product_return_moves:
                        #     if e.product_id.id in invoice_lines_copy:
                        #         invoice_lines_copy[e.product_id.id].write({
                        #             'quantity': e.quantity
                        #         })
                        #         invoice_lines_update.append(invoice_lines_copy[e.product_id.id].id)
                        if invoice:
                            refund.with_context({'active_ids': [invoice.id]}).compute_refund(mode='refund')
                            credit_note = self.env['account.invoice'].search([('refund_invoice_id', '=', invoice.id)])
                            for e in credit_note:
                                if e.state != 'paid':
                                    # e.invoice_line_ids = invoice_lines
                                    e.write({
                                        'invoice_line_ids': [(6, 0, invoice_lines_update)]
                                    })
                                    e.action_invoice_open()
                                    if exist_order.payment_method == 'cod':
                                        journal_id = self.env['account.journal'].search([('code', '=', 'CSH1')]).id
                                    elif exist_order.payment_method == 'online_payment':
                                        journal_id = self.env['account.journal'].search([('code', '=', 'BNK1')]).id
                                    payment = self.env['account.payment'].create({
                                        'invoice_ids': [(4, e.id, None)],
                                        'amount': e.amount_total,
                                        'payment_date': date.today(),
                                        'communication': e.number,
                                        'payment_type': 'outbound',
                                        'journal_id': journal_id,
                                        'partner_type': 'customer',
                                        'payment_method_id': 1,
                                        'partner_id': e.partner_id.id
                                    })
                                    payment.action_validate_invoice_payment()
                        exist_order.write({
                            'state': 'canceled',
                            'status': 'canceled'
                        })
                        self.env.cr.execute(
                            """UPDATE sale_order SET state = %s WHERE id = %s""",
                            ('cancel', exist_order.odoo_id.id))

    def fetch_source(self):
        if not self.auto_fetching:
            url = self.web_url
            token = self.access_token
            location = Location(url, token, True)
            backend_id = self.id
            pull_history = self.env['magento.pull.history'].search(
                [('backend_id', '=', backend_id), ('name', '=', 'sources')])
            sources = location.list_all_sources()
            location.insert_source(sources['items'], backend_id, url, token, self)
            if not len(pull_history) > 0:
                self.env['magento.pull.history'].create({
                    'name': 'sources',
                    'sync_date': datetime.today(),
                    'backend_id': backend_id
                })
            else:
                self.env['magento.pull.history'].write({
                    'sync_date': datetime.today(),
                })
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Fetch sources successful"
                },
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'popup.dialog',
                'target': 'new',
                'context': {
                    'default_message': "Sources are fetching by schedule action, you can fetch sale orders manually after schedule action finish"
                },
            }

    @api.multi
    def auto_fetch_magento_data(self):
        """ Automatic Pull Data From Instance Follow Standard Process"""
        if not self.id:
            self = self.env['magento.backend'].search([], limit=1)
        # search and check if = false then run
        self.env.cr.execute("""UPDATE magento_backend SET auto_fetching = FALSE WHERE id = %s""", (self.id,))
        self.env.cr.commit()
        if not self.auto_fetching:
            heineken_product = self.env['product.product'].search([('is_heineken_product', '=', True)])
            qty_previous_day = self.env['product.product'].browse(heineken_product.ids)._compute_quantities_dict(
                self._context.get('lot_id'),
                self._context.get(
                    'owner_id'),
                self._context.get(
                    'package_id'),
                self._context.get(
                    'from_date'),
                to_date=fields.datetime.now())
            self.fetch_sale_orders()
