# -*- coding: UTF-8 -*-

from datetime import date

from .customer import get_state_id, get_country_id
from ..magento.rest import Client


class Order(Client):
    """
    Allows to import orders.
    """
    __slots__ = ()

    def list(self, pageSize, currentPage):

        return self.call('rest/V1/orders',
                         'searchCriteria[currentPage]=' + str(currentPage) + '&searchCriteria[pageSize]=' + str(
                             pageSize))

    def listShipment(self):
        return self.call('rest/V1/shipments', 'searchCriteria')

    def list_gt_created_at_after_sync(self, created_at):

        return self.call('rest/V1/orders',
                         'searchCriteria[filter_groups][0][filters][0][field]=created_at&'
                         'searchCriteria[filter_groups][0][filters][0][value]=' + str(created_at) + '&'
                                                                                                    'searchCriteria[filter_groups][0][filters][0][condition_type]=gt')

    def list_order_updated_at_after_sync(self, updated_at):
        return self.call('rest/V1/orders',
                         'searchCriteria[filter_groups][0][filters][0][field]=updated_at&'
                         'searchCriteria[filter_groups][0][filters][0][value]=' + str(updated_at) + '&'
                                                                                                    'searchCriteria[filter_groups][0][filters][0][condition_type]=gt'
                         + '&searchCriteria[filter_groups][0][filters][1][field]=created_at&'
                           'searchCriteria[filter_groups][0][filters][1][value]=' + str(updated_at) + '&'
                                                                                                      'searchCriteria[filter_groups][0][filters][1][condition_type]=gt')

    def list_gt_update_at_shipment(self, updated_at):
        print('rest/V1/shipments',
              'searchCriteria[filter_groups][0][filters][0][field]=created_at&'
              'searchCriteria[filter_groups][0][filters][0][value]=' + str(updated_at) + '&'
                                                                                         'searchCriteria[filter_groups][0][filters][0][condition_type]=gt')
        return self.call('rest/V1/shipments',
                         'searchCriteria[filter_groups][0][filters][0][field]=created_at&'
                         'searchCriteria[filter_groups][0][filters][0][value]=' + str(updated_at) + '&'
                                                                                                    'searchCriteria[filter_groups][0][filters][0][condition_type]=gt')

    def importer_sale(self, orders, backend_id, backend_name, prefix_order, context=None):
        if len(orders) > 0:
            sale_orders = []
            magento_sale_orders = []
            shipment_orders_lines = []
            sale_orders_lines_json = []
            default_consumer_product_id = 1
            default_service_product_id = 1
            partner_id = context.env.ref('magento2_connector.create_customer_guest').id
            default_magento_partner_odoo_id = -1
            default_magento_partner_odoo = context.env['magento.res.partner'].sudo().search(
                [('backend_id', '=', backend_id), ('odoo_id', '=', partner_id)], limit=1)
            if not default_magento_partner_odoo:
                website_list = context.env['magento.website'].sudo().search([('backend_id', '=', backend_id)])
                for website_item in website_list:
                    website_store_view = context.env['magento.storeview'].sudo().search(
                        [('backend_id', '=', backend_id), ('website_id', '=', website_item.id)])
                    for website_store_view_item in website_store_view:
                        new_magento_res_partner = context.env['magento.res.partner'].sudo().create({
                            'backend_id': backend_id,
                            'odoo_id': partner_id,
                            'website_id': website_item.id,
                            'storeview_id': website_store_view_item.id
                        })

                        default_magento_partner_odoo_id = new_magento_res_partner.id
            else:
                default_magento_partner_odoo_id = default_magento_partner_odoo.id

            for order in orders:
                # odoo
                partner_id = context.env.ref('magento2_connector.create_customer_guest').id

                if order['customer_group_id'] == 0:
                    customers = []
                    # billing_address
                    billing_address = order['billing_address']
                    if 'region' not in billing_address:
                        billing_address['region'] = 0
                    if 'region_code' not in billing_address:
                        billing_address['region_code'] = 0
                    billing_address_state_id = get_state_id(billing_address['region'], billing_address['region_code'],
                                                            context)
                    billing_address_country_id = get_country_id(billing_address['country_id'], context)
                    billing_address_data = (
                        billing_address['firstname'] + " " + billing_address['lastname'], billing_address['street'][0],
                        billing_address['postcode'], billing_address['city'], billing_address_state_id,
                        billing_address_country_id,
                        billing_address['email'], billing_address['telephone'], True, 'invoice')
                    customers.append(billing_address_data)

                    # shipping address
                    if 'address' in order['extension_attributes']['shipping_assignments'][0]['shipping']:
                        shipping_address = order['extension_attributes']['shipping_assignments'][0]['shipping'][
                            'address']
                        if not 'region' in shipping_address:
                            shipping_address['region'] = 0
                        if not 'region_code' in shipping_address:
                            shipping_address['region_code'] = 0
                        shipping_address_state_id = get_state_id(shipping_address['region'],
                                                                 shipping_address['region_code'],
                                                                 context)
                        shipping_address_country_id = get_country_id(shipping_address['country_id'], context)
                        shipping_address_data = (
                            shipping_address['firstname'] + " " + shipping_address['lastname'],
                            shipping_address['street'][0],
                            shipping_address['postcode'], shipping_address['city'], shipping_address_state_id,
                            shipping_address_country_id, shipping_address['email'], shipping_address['telephone'], True,
                            'delivery')
                        customers.append(shipping_address_data)

                        context.env.cr.execute(
                            """INSERT INTO res_partner (name, street,zip,city,state_id,country_id, email,phone, active,type) VALUES {values} RETURNING id""".format(
                                values=", ".join(["%s"] * len(customers))), tuple(customers))

                        address_ids = context.env.cr.fetchall()
                        partner_invoice_id = address_ids[0][0]
                        partner_shipping_id = address_ids[1][0]
                else:
                    customers = []
                    # init guest partner
                    if 'customer_id' in order:
                        context.env.cr.execute(
                            "SELECT odoo_id FROM magento_res_partner WHERE backend_id=%s AND external_id=%s LIMIT 1" % (
                                backend_id, order['customer_id']))
                        current_partner = context.env.cr.fetchone()
                        if current_partner and len(current_partner) > 0:
                            partner_id = current_partner[0]

                    if 'customer_address_id' in order['billing_address']:
                        if 'customer_id' in order:
                            address_id = order['customer_id']
                        else:
                            address_id = 0
                        b = context.env.cr.execute(
                            "SELECT id FROM res_partner WHERE magento_customer_id=%s AND magento_address_id=%s AND backend_id=%s LIMIT 1" % (
                                address_id, order['billing_address']['customer_address_id'], backend_id))
                        if b != None:
                            partner_shipping_id = context.env.cr.fetchone()[0]
                        else:
                            billing_address = order['billing_address']
                            if 'region' not in billing_address:
                                billing_address['region'] = 0
                            if 'region_code' not in billing_address:
                                billing_address['region_code'] = 0
                            billing_address_state_id = get_state_id(billing_address['region'],
                                                                    billing_address['region_code'],
                                                                    context)
                            billing_address_country_id = get_country_id(billing_address['country_id'], context)
                            billing_address_data = (
                                billing_address['firstname'] + " " + billing_address['lastname'],
                                billing_address['street'][0],
                                billing_address['postcode'], billing_address['city'], billing_address_state_id,
                                billing_address_country_id,
                                billing_address['email'], billing_address['telephone'], True, 'invoice')
                            customers.append(billing_address_data)

                    else:
                        billing_address = order['billing_address']
                        if 'region' not in billing_address:
                            billing_address['region'] = 0
                        if 'region_code' not in billing_address:
                            billing_address['region_code'] = 0
                        billing_address_state_id = get_state_id(billing_address['region'],
                                                                billing_address['region_code'],
                                                                context)
                        billing_address_country_id = get_country_id(billing_address['country_id'], context)
                        billing_address_data = (
                            billing_address['firstname'] + " " + billing_address['lastname'],
                            billing_address['street'][0],
                            billing_address['postcode'], billing_address['city'], billing_address_state_id,
                            billing_address_country_id,
                            billing_address['email'], billing_address['telephone'], True, 'invoice')
                        customers.append(billing_address_data)

                    # address shipping
                    if 'customer_address_id' in order['extension_attributes']['shipping_assignments'][0]['shipping'][
                        'address']:
                        partner_shipping_id = \
                            order['extension_attributes']['shipping_assignments'][0]['shipping']['address'][
                                'customer_address_id']
                    else:
                        partner_shipping_id = 0
                    if 'customer_id' in order:
                        customer_id = order['customer_id']
                    else:
                        customer_id = 0
                    c = context.env.cr.execute(
                        "SELECT id FROM res_partner WHERE magento_customer_id=%s AND magento_address_id=%s AND backend_id=%s LIMIT 1" % (
                            customer_id, partner_shipping_id, backend_id))

                    if c != None:
                        partner_shipping_id = context.env.cr.fetchone()[0]
                    else:
                        if 'address' in order['extension_attributes']['shipping_assignments'][0]['shipping']:
                            shipping_address = order['extension_attributes']['shipping_assignments'][0]['shipping'][
                                'address']
                            if not 'region' in shipping_address:
                                shipping_address['region'] = 0
                            if not 'region_code' in shipping_address:
                                shipping_address['region_code'] = 0
                            shipping_address_state_id = get_state_id(shipping_address['region'],
                                                                     shipping_address['region_code'],
                                                                     context)
                            shipping_address_country_id = get_country_id(shipping_address['country_id'], context)
                            shipping_address_data = (
                                shipping_address['firstname'] + " " + shipping_address['lastname'],
                                shipping_address['street'][0],
                                shipping_address['postcode'], shipping_address['city'], shipping_address_state_id,
                                shipping_address_country_id, shipping_address['email'], shipping_address['telephone'],
                                True,
                                'delivery')
                            customers.append(shipping_address_data)
                    context.env.cr.execute(
                        """INSERT INTO res_partner (name, street,zip,city,state_id,country_id, email,phone, active,type) VALUES {values} RETURNING id""".format(
                            values=", ".join(["%s"] * len(customers))), tuple(customers))

                    address_ids = context.env.cr.fetchall()
                    partner_invoice_id = address_ids[0][0]
                    partner_shipping_id = address_ids[1][0]

                name = prefix_order + order['increment_id']
                # product_id = order['items'][0]['item_id']
                # magento
                base_currency_code = order['order_currency_code']
                currency_id = context.env.ref('base.' + str(base_currency_code))
                currency = currency_id.id
                product_price_list_ids = currency_id.product_price_list_ids
                if not product_price_list_ids:
                    context.env.cr.execute("""INSERT INTO product_pricelist (name,active,currency_id,backend_id) VALUES (%s, %s, %s, %s) 
                                              ON CONFLICT (name,backend_id) DO UPDATE SET (name,currency_id) = (EXCLUDED.name, EXCLUDED.currency_id) RETURNING id"""
                                           , ('magento-' + str(base_currency_code), True, currency_id.id, backend_id))
                    product_price_list_id = context.env.cr.fetchone()[0]
                else:
                    product_price_list_id = product_price_list_ids[0].id

                store_id = order['store_id']
                order_id = order['entity_id']
                carrier_id = None

                # if order['status'] in ['closed']:
                #     status = 'done'
                #     confirmation_date = order['created_at']
                # elif order['status'] in ['canceled']:
                #     status = 'cancel'
                #     confirmation_date = order['created_at']
                # elif order['status'] in ['processing', 'complete']:
                #     status = 'sale'
                #     confirmation_date = order['created_at']
                # else:
                #     status = 'sent'
                #     confirmation_date = None
                # if 'state' in order:
                #     state = order['state']
                # else:
                #     state = 'N/A'

                # if order['state'] in ['closed']:
                #     status = 'cancel'
                #     confirmation_date = order['created_at']
                # elif order['state'] in ['canceled']:
                #     status = 'cancel'
                #     confirmation_date = order['created_at']
                # elif order['status'] in ['processing', 'shipping']:
                #     status = 'sale'
                #     confirmation_date = order['created_at']
                # elif order['status'] in ['complete']:
                #     status = 'done'
                # else:
                #     status = 'sent'
                #     confirmation_date = order['created_at']

                if 'state' in order:
                    state = order['state']
                    if state in ['canceled', 'closed', 'holded']:
                        state = 'cancel'
                    elif state in ['processing', 'shipping']:
                        state = 'sale'
                    elif state in ['new', 'pending_payment', 'payment_review']:
                        state = 'sent'
                    elif state in ['complete']:
                        state = 'done'
                else:
                    state = 'N/A'

                print(order['state'])
                if order['state'] in ['processing', 'shipping', 'complete']:
                    # get shipment_amount and shipment_method
                    shipment_amount = order['extension_attributes']['shipping_assignments'][0]['shipping']['total'][
                        'shipping_amount']
                    if 'method' in order['extension_attributes']['shipping_assignments'][0]['shipping']:
                        shipment_method = order['extension_attributes']['shipping_assignments'][0]['shipping']['method']
                    else:
                        shipment_method = None
                    # magento_sale_orders.append((store_id, backend_id, order_id, shipment_amount, shipment_method, state))

                    magento_sale_orders.append(
                        (store_id, backend_id, order_id, shipment_amount, shipment_method, order['state'],
                         order['status']))

                    product_items = order['items']
                    order_lines = []
                    coupon_code = ''
                    if 'coupon_code' in order:
                        coupon_code = order['coupon_code']
                    # loc de loai di cac order item cha
                    tax_percent_fix = 0
                    # list_name_product = []
                    for product_item in product_items:
                        if tax_percent_fix == 0:
                            if 'tax_percent' in product_item:
                                tax_percent_fix = product_item['tax_percent']
                        if product_item['product_type'] != 'configurable':
                            # list_name_product.append(product_item['name'])
                            tax_percent = 0
                            if 'tax_percent' in product_item:
                                tax_percent = product_item['tax_percent']
                                if tax_percent > 0:
                                    tax_percent_fix = tax_percent
                            product_id = product_item['product_id']
                            default_code = product_item['sku']

                            context.env.cr.execute("""
                                                           SELECT * FROM combine_id({backend_id},{amount},'{default_code}',{external_id})""".
                                                   format(backend_id=backend_id, amount=tax_percent_fix,
                                                          default_code=default_code,
                                                          external_id=product_id))

                            tmp = context.env.cr.fetchone()

                            if tmp:
                                account_tax_id = (tmp[0] if tmp[0] else '')
                                if tmp[2]:
                                    product_id = tmp[2]
                                elif tmp[1]:
                                    product_id = tmp[1]
                                else:
                                    if 'weight' in product_item and product_item['weight'] > 0:
                                        product_id = context.env.ref(
                                            'magento2_connector.magento_sample_product_consumable').id
                                    else:
                                        product_id = context.env.ref(
                                            'magento2_connector.magento_sample_product_service').id
                                # insert in sale_order_line
                                # neu order item co truong parent_item_id va parent_item_id > 0
                            item_id_of_product = product_item['item_id']

                            if 'parent_item' in product_item:
                                order_lines.append(
                                    (0, 0, {'name': product_item['name'], 'product_id': product_id,
                                            'product_uom_qty': product_item['parent_item']['qty_ordered'],
                                            'qty_delivered': product_item['parent_item']['qty_shipped'],
                                            'qty_invoiced': product_item['parent_item']['qty_invoiced'],
                                            'price_unit': product_item['parent_item']['price'],
                                            'discount': 0,
                                            'tax_id': [(6, 0, [])]}))
                            else:
                                order_lines.append(
                                    (0, 0, {'name': product_item['name'], 'product_id': product_id,
                                            'product_uom_qty': product_item['qty_ordered'],
                                            'qty_delivered': product_item['qty_shipped'],
                                            'qty_invoiced': product_item['qty_invoiced'],
                                            'price_unit': product_item['price'],
                                            'discount': 0,
                                            'tax_id': [(6, 0, [])]}))

                    if shipment_method == 'flatrate_flatrate':
                        shipment_product_product = context.env.ref(
                            'magento2_connector.magento_flat_rate_shipping_product')
                        shipment_product_product_id = shipment_product_product.id
                        shipment_product_product_name = shipment_product_product.name
                        delivery_method = context.env['delivery.carrier'].search(
                            [('name', 'like', '%Flat Rate Shipping%')])
                        carrier_id = delivery_method.ids[0]

                        order_lines.append((0, 0, {'name': shipment_product_product_name,
                                                   'price_unit': shipment_amount,
                                                   'price_subtotal': shipment_amount,
                                                   'product_id': shipment_product_product_id,
                                                   'product_uom_qty': 1,
                                                   'product_uom': 1,
                                                   'tax_id': [(6, 0, [])],
                                                   'is_delivery': True}))
                    if shipment_method == 'freeshipping_freeshipping':
                        shipment_product_product = context.env.ref('magento2_connector.magento_free_shipping_product')
                        shipment_product_product_id = shipment_product_product.id
                        shipment_product_product_name = shipment_product_product.name
                        delivery_method = context.env['delivery.carrier'].search(
                            [('name', 'like', '%Free Shipping %')])
                        carrier_id = delivery_method.ids[0]

                        order_lines.append((0, 0, {'name': shipment_product_product_name,
                                                   'price_unit': shipment_amount,
                                                   'price_subtotal': shipment_amount,
                                                   'product_id': shipment_product_product_id,
                                                   'product_uom_qty': 1,
                                                   'product_uom': 1,
                                                   'tax_id': [(6, 0, [])],
                                                   'is_delivery': True}))
                    if shipment_method == 'getswift_getswift':
                        delivery_method = context.env['delivery.carrier'].search(
                            [('name', 'like', '%GetSwift%')])
                        carrier_id = delivery_method.ids[0]
                    if 'tax_amount' in order and order['tax_amount'] > 0:
                        tax_amount = order['tax_amount']
                        tax_real_product_id = context.env.ref('magento2_connector.tax_real')
                        tax_fake_product_id = context.env.ref('magento2_connector.tax_fake')
                        tax_percent_id = context.env.ref('magento2_connector.tax_100')
                        order_lines.append((0, 0, {'name': "Tax",
                                                   'price_unit': tax_amount,
                                                   'price_subtotal': tax_amount,
                                                   'product_id': tax_real_product_id.id,
                                                   'product_uom_qty': 1,
                                                   'product_uom': 1,
                                                   'tax_id': [(4, tax_percent_id.id)],
                                                   'is_delivery': False}))
                        order_lines.append(
                            (0, 0, {'name': "To keep correct amount on Tax (for Accounting) and grant total",
                                    'price_unit': -tax_amount,
                                    'price_subtotal': -tax_amount,
                                    'product_id': tax_fake_product_id.id,
                                    'product_uom_qty': 1,
                                    'product_uom': 1,
                                    'is_delivery': False}))
                    if coupon_code != '':
                        discount_amount = order['discount_amount']
                        order_line_discount = context.env.ref('magento2_connector.discount_record')
                        order_lines.append(
                            (0, 0, {'name': ("Apply discount code: " + str(coupon_code)) if coupon_code != '' else None,
                                    'price_unit': discount_amount,
                                    'price_subtotal': discount_amount,
                                    'product_id': order_line_discount.id,
                                    'product_uom_qty': 1,
                                    'product_uom': 1,
                                    'is_delivery': False}))
                    # insert in sale_order with shipment

                    if order['payment']['method'] == 'eghlpayment':
                        payment_method = 'online_payment'
                    elif order['payment']['method'] == 'cashondelivery':
                        payment_method = 'cod'

                    if partner_id == context.env.ref('magento2_connector.create_customer_guest').id:
                        old_partner = context.env['res.partner'].search(
                            [('email', '=', order['customer_email']), ('active', '=', True), '|',
                             ('type', '=', 'contact'),
                             ('type', '=', False)])
                        if len(old_partner) > 0:
                            partner_id = old_partner.ids[0]
                        else:
                            partner_id = partner_invoice_id

                    #add source on sale order
                    if 'order_source_code' in order['extension_attributes']:
                        source = context.env['stock.location'].search(
                            [('magento_source_code', '=', order['extension_attributes']['order_source_code'])])
                    else:
                        source = False
                    sale_orders.append({'information':
                                            {'name': name,
                                             'partner_id': partner_id,
                                             'partner_invoice_id': partner_invoice_id,
                                             'partner_shipping_id': partner_shipping_id,
                                             'pricelist_id': product_price_list_id,
                                             # 'state': status,
                                             'confirmation_date': order['created_at'],
                                             'order_line': order_lines if len(order_lines) > 0 else '',
                                             'has_delivery': True if shipment_method else '',
                                             'carrier_id': carrier_id if carrier_id is not None else False,
                                             'is_magento_sale_order': True,
                                             'currency_id': currency,
                                             'payment_method': payment_method,
                                             'location_id': source.id if len(source) > 0 else False
                                             # 'note': ("Apply discount code:" + str(coupon_code)) if coupon_code != '' else None
                                             },
                                        'status': state
                                        })
                    # trường hợp address được add trên front end magento, sẽ được cập nhật khi có sale order ship tới địa chỉ này
                    if 'address' in order['extension_attributes']['shipping_assignments'][0][
                        'shipping'] and 'customer_id' in order:
                        shipping_address = order['extension_attributes']['shipping_assignments'][0]['shipping'][
                            'address']
                        if 'customer_address_id' in shipping_address:
                            customer_address_id = shipping_address['customer_address_id']
                            current_customer_id = order['customer_id']
                            this_partner = context.env['res.partner'].search(
                                [('magento_customer_id', '=', current_customer_id),
                                 ('magento_address_id', '=', customer_address_id)])
                            if not 'region' in shipping_address:
                                shipping_address['region'] = 0
                            if not 'region_code' in shipping_address:
                                shipping_address['region_code'] = 0
                            shipping_address_state_id = get_state_id(shipping_address['region'],
                                                                     shipping_address['region_code'],
                                                                     context)
                            shipping_address_country_id = get_country_id(shipping_address['country_id'], context)
                            new_customer = []
                            if not this_partner:
                                shipping_address_data = (
                                    shipping_address['firstname'] + " " + shipping_address['lastname'],
                                    shipping_address['street'][0],
                                    shipping_address['postcode'], shipping_address['city'], shipping_address_state_id,
                                    shipping_address_country_id, shipping_address['email'],
                                    shipping_address['telephone'],
                                    True,
                                    'delivery', current_customer_id, customer_address_id, True, True,
                                    current_customer_id)
                                new_customer.append(shipping_address_data)
                                context.env.cr.execute(
                                    """INSERT INTO res_partner (name, street,zip,city,state_id,country_id, email,phone, active,type,magento_customer_id,magento_address_id,customer,is_from_magento,magento_id) VALUES {values} RETURNING id""".format(
                                        values=", ".join(["%s"] * len(new_customer))), tuple(new_customer))
                                current_partner_id = context.env.cr.fetchone()
                                context.env.cr.execute(
                                    """SELECT id FROM magento_res_partner WHERE external_id = %s and backend_id =%s""",
                                    (current_customer_id, backend_id))
                                magento_partner_odoo_id = context.env.cr.fetchone()
                                if not magento_partner_odoo_id:
                                    magento_partner_odoo_id = default_magento_partner_odoo_id
                                context.env.cr.execute(
                                    """INSERT INTO magento_address (odoo_id,magento_partner_id,backend_id) VALUES (%s,%s,%s)""",
                                    (current_partner_id, magento_partner_odoo_id, backend_id))
                    else:  # truong hop dia chi moi tao tren magento la billing address
                        if 'billing_address' in order and 'customer_id' in order:
                            shipping_address = order['billing_address']
                            if 'customer_address_id' in shipping_address:
                                customer_address_id = shipping_address['customer_address_id']
                                current_customer_id = order['customer_id']
                                this_partner = context.env['res.partner'].search(
                                    [('magento_customer_id', '=', current_customer_id),
                                     ('magento_address_id', '=', customer_address_id)])
                                if not 'region' in shipping_address:
                                    region = ""
                                else:
                                    region = shipping_address['region']
                                region_code = ""
                                if not 'region_code' in shipping_address:
                                    shipping_address['region_code'] = ""
                                else:
                                    region_code = shipping_address['region_code']
                                shipping_address_state_id = get_state_id(region,
                                                                         region_code,
                                                                         context)
                                shipping_address_country_id = get_country_id(shipping_address['country_id'], context)
                                new_customer = []
                                if not this_partner:
                                    shipping_address_data = (
                                        shipping_address['firstname'] + " " + shipping_address['lastname'],
                                        shipping_address['street'][0],
                                        shipping_address['postcode'], shipping_address['city'],
                                        shipping_address_state_id,
                                        shipping_address_country_id, shipping_address['email'],
                                        shipping_address['telephone'],
                                        True,
                                        'delivery', current_customer_id, customer_address_id, True, True,
                                        current_customer_id)
                                    new_customer.append(shipping_address_data)
                                    context.env.cr.execute(
                                        """INSERT INTO res_partner (name, street,zip,city,state_id,country_id, email,phone, active,type,magento_customer_id,magento_address_id,customer,is_from_magento,magento_id) VALUES {values} RETURNING id""".format(
                                            values=", ".join(["%s"] * len(new_customer))), tuple(new_customer))
                                    current_partner_id = context.env.cr.fetchone()
                                    context.env.cr.execute(
                                        """SELECT id FROM magento_res_partner WHERE external_id = %s and backend_id =%s""",
                                        (current_customer_id, backend_id))
                                    magento_partner_odoo_id = context.env.cr.fetchone()
                                    if not magento_partner_odoo_id:
                                        magento_partner_odoo_id = default_magento_partner_odoo_id
                                    context.env.cr.execute(
                                        """INSERT INTO magento_address (odoo_id,magento_partner_id,backend_id) VALUES (%s,%s,%s)""",
                                        (current_partner_id, magento_partner_odoo_id, backend_id))

            drinkies_sale_team = context.env.ref('advanced_sale.sale').id
            sale_order_ids = []
            sale_order_created = []

            if sale_orders and len(sale_orders) > 0:
                # for e in sale_orders:
                for e in sale_orders:
                    res = context.env['sale.order'].sudo().create(e['information'])

                    res.order_reference_id = res.name
                    res.team_id = drinkies_sale_team
                    # res.action_confirm()
                    # context.env.cr.execute(
                    #     """UPDATE sale_order SET state = %s WHERE id = %s""", (str(e['status']), res.id))
                    sale_order_ids.append((res.id,))
                    sale_order_created.append({
                        'information': res,
                        'status': e['status']
                    })

                magento_sale_orders_mapped_id = tuple(map(lambda x, y: x + y, magento_sale_orders, sale_order_ids))
                if magento_sale_orders and len(magento_sale_orders) > 0:
                    context.env.cr.execute(
                        """INSERT INTO magento_sale_order (store_id, backend_id, external_id,shipment_amount,shipment_method, state,status,odoo_id) VALUES {values} RETURNING id""".format(
                            values=", ".join(["%s"] * len(magento_sale_orders_mapped_id))),
                        tuple(magento_sale_orders_mapped_id))

                for e in sale_order_created:
                    e['information'].action_confirm()

                    context.env.cr.execute(
                        """UPDATE sale_order SET state = %s WHERE id = %s""", (str(e['status']), e['information'].id))

    def import_shipment_on_sale_order(self, external_sale_order_id, shipment_product, backend_id, context=None):
        product_order_line_id = []
        magento_sale_order = context.env['magento.sale.order'].sudo().search(
            [('external_id', '=', external_sale_order_id), ('backend_id', '=', backend_id)])
        if len(magento_sale_order.odoo_id.ids) > 0:
            odoo_sale_order_id = magento_sale_order.odoo_id.ids[0]
            stock_picking = context.env['stock.picking'].search([('sale_id', '=', odoo_sale_order_id)])
            so = context.env['sale.order'].sudo().browse(odoo_sale_order_id)
            if not stock_picking:
                if so.state != 'done' and so.state != 'cancel':
                    so.action_confirm()
                stock_picking = so.picking_ids
            if len(stock_picking.ids) > 0:
                stock_picking_id = stock_picking.ids[0]
                # # add picking_ids to sale_order
                # context.env.cr.execute("""UPDATE sale_order SET picking_ids = %s WHERE id = %s """,
                #                        (stock_picking_id, odoo_sale_order_id))

                orders_line = context.env['sale.order.line'].search([('order_id', '=', odoo_sale_order_id)])
                orders_line_id = orders_line.ids
                for e in orders_line_id:
                    order_line = context.env['sale.order.line'].search([('id', '=', e)])
                    order_line_product_id = order_line.product_id.ids[0]
                    product_order_line_id.append(order_line_product_id)

                for e in shipment_product:
                    product_shipment = context.env['magento.product.product'].search([('external_id', '=', e[0])])

                    if len(product_shipment.odoo_id.ids) > 0:
                        product_shipment_id = product_shipment.odoo_id.ids[0]

                        if product_shipment_id in product_order_line_id:
                            stock_move_line = context.env['stock.move.line'].search(
                                [('picking_id', '=', stock_picking_id), ('product_id', '=', product_shipment_id)])
                            if len(stock_move_line) > 0:
                                stock_move_line.write({
                                    'qty_done': e[1]
                                })
                            else:
                                stock_move = context.env['stock.move'].search(
                                    [('picking_id', '=', stock_picking_id), ('product_id', '=', product_shipment_id)])
                                context.env['stock.move.line'].create({
                                    'picking_id': stock_move.picking_id.id,
                                    'location_id': stock_move.location_id.id,
                                    'location_dest_id': stock_move.location_dest_id.id,
                                    'product_id': stock_move.product_id.id,
                                    'qty_done': e[1],
                                    'move_id': stock_move.id,
                                    'product_uom_id': stock_move.product_uom.id
                                })
                    else:
                        product_shipment_id = None

                        if product_shipment_id in product_order_line_id:
                            if len(stock_move_line) > 0:
                                stock_move_line.write({
                                    'qty_done': e[1]
                                })
                            else:
                                stock_move = context.env['stock.move'].search(
                                    [('picking_id', '=', stock_picking_id), ('product_id', '=', product_shipment_id)])
                                context.env['stock.move.line'].create({
                                    'picking_id': stock_move.picking_id.id,
                                    'location_id': stock_move.location_id.id,
                                    'location_dest_id': stock_move.location_dest_id.id,
                                    'product_id': stock_move.product_id.id,
                                    'qty_done': e[1],
                                    'move_id': stock_move.id,
                                    'product_uom_id': stock_move.product_uom.id
                                })
                context.env['stock.picking'].sudo().browse(stock_picking_id).action_done()

                if magento_sale_order.state == 'complete':
                    # magento_invoices = context.env['magento.account.invoice'].search(
                    #     [('magento_order_id', '=', magento_sale_order.id), ('backend_id', '=', backend_id)])
                    # if len(magento_invoices.odoo_id.ids) > 0:
                    #     odoo_invoice_id = magento_sale_order.odoo_id.ids[0]
                    #     so.invoice_ids = odoo_invoice_id
                    magento_sale_order.write({'status': 'done'})
                    context.env.cr.execute("""UPDATE sale_order SET state = %s , invoice_status = %s WHERE id = %s """,
                                           ('done', 'invoiced', odoo_sale_order_id))
            else:
                # print('cant find odoo stock picking for order ' + str(odoo_sale_order_id))
                pass
        else:
            print('cant find odoo sale order ' + str(external_sale_order_id))

    def import_shipment(self, shipments, backend_id, context=None):
        for shipment in shipments['items']:
            # total_qty = shipment['total_qty']
            sale_order_id = shipment['order_id']
            product = []
            for e in shipment['items']:
                product.append((e['product_id'], e['qty']))
            self.import_shipment_on_sale_order(sale_order_id, product, backend_id, context)
