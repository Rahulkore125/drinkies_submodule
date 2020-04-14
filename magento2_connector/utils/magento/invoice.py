# -*- coding: UTF-8 -*-

from ..magento.rest import Client


class Invoice(Client):
    """
    Allows to import invoice.
    """
    __slots__ = ()

    def list(self, currentPage, pageSize):

        return self.call('rest/V1/invoices',
                         'searchCriteria[currentPage]=' + str(currentPage) + '&searchCriteria[pageSize]=' + str(
                             pageSize))

    def importer_invoice_line(self, ):
        pass

    def list_all(self):
        return self.call('rest/V1/invoices', 'searchCriteria')

    def list_gt_updated_at(self, updated_at):
        return self.call('rest/V1/invoices',
                         'searchCriteria[filter_groups][0][filters][0][field]=updated_at&searchCriteria[filter_groups][0][filters][0][value]=' + str(
                             updated_at) + '&searchCriteria[filter_groups][0][filters][0][condition_type]=gt')

    def get_array_tax_percent(self, context=None):
        taxes = context.env['account.tax'].sudo().search([])
        array_tax_percent = []
        for rec in taxes:
            array_tax_percent.append(rec.amount)
        return array_tax_percent

    def importer_invoice(self, invoices, backend_id, prefix, journal_id, payment_journal, context=None):
        array_odoo_invoices = []
        array_magento_invoices = []
        for invoice in invoices:
            invoice_id = invoice['entity_id']
            magento_invoice = context.env['magento.account.invoice'].sudo().search(
                [('external_id', '=', invoice_id), ('backend_id', '=', backend_id)])
            if magento_invoice:
                if magento_invoice.state == 'open' and invoice['state'] == 2:
                    # change invoice from open to paid
                    account_payment = context.env['account.payment'].sudo().create({
                        'amount': invoice.amount_total,
                        'currency_id': invoice.currency_id.id,
                        'payment_date': invoice.date,
                        'journal_id': payment_journal,
                        'communication': invoice.number,
                        'invoice_ids': [(6, 0, [invoice.id])],
                        'payment_method_id': context.env.ref('payment.account_payment_method_electronic_in').id,
                        'payment_type': 'inbound',
                        'partner_type': 'customer',
                        'partner_id': invoice.partner_id.id,
                    })
                    context.env['account.payment'].sudo().browse(
                        account_payment.id).action_validate_invoice_payment()
                    magento_invoice.write({
                        'state': 'paid'
                    })
                elif magento_invoice.state == 'open' and invoice['state'] == 3:
                    # change invoice from open to cancel
                    odoo_invoice_id = magento_invoice.odoo_id.ids[0]
                    odoo_invoice = context.env['account.invoice'].search([('id', '=', odoo_invoice_id)])
                    odoo_invoice.action_invoice_cancel()

                    magento_invoice.write({
                        'state': 'cancel'
                    })
                elif magento_invoice.state == 'paid' and invoice['state'] == 3:
                    # viet lai thu tu chay trong odoo, thu tu tim cac record_id, thu tu xoa cac record
                    # delete invoice'money on account journal
                    # change invoice from paid to cancel
                    odoo_invoice_id = magento_invoice.odoo_id.ids[0]
                    odoo_invoice = context.env['account.invoice'].search([('id', '=', odoo_invoice_id)])

                    # odoo_invoice.write({
                    #     'move_id': None
                    # })

                    context.env.cr.execute(
                        """SELECT account_move_line_id FROM account_invoice_account_move_line_rel WHERE account_invoice_id = %s""",
                        (odoo_invoice_id,))

                    account_move_line_id = context.env.cr.fetchall()
                    account_move_line_id_id = account_move_line_id[0][0]
                    context.env.cr.execute("""UPDATE account_invoice SET move_id = %s WHERE id = %s """,
                                           (None, magento_invoice.odoo_id.ids[0]))
                    context.env.cr.execute("""DELETE FROM account_partial_reconcile WHERE credit_move_id = %s""" %
                                           (account_move_line_id_id,))

                    context.env.cr.execute("""DELETE FROM account_move WHERE ref = %s""", (odoo_invoice.number,))
                    magento_invoice.write({
                        'state': 'cancel'
                    })
                    odoo_invoice.action_invoice_cancel()
            else:
                # insert new invoice
                amount_total_signed = invoice['grand_total']
                increment_id = invoice['increment_id']
                # convert to odoo
                currency = invoice['order_currency_code']
                currency_id = context.env.ref('base.' + str(currency))
                if not currency_id.active:
                    currency_id.active = True
                order_id = invoice['order_id']
                state_id = invoice['state']
                if state_id == 1:
                    state = 'open'
                elif state_id == 2:
                    state = 'paid'
                else:
                    state = 'cancel'
                # get partner_id
                context.env.cr.execute(
                    """SELECT partner_id FROM sale_order WHERE id in (SELECT odoo_id FROM magento_sale_order WHERE external_id = %s AND backend_id = %s )""",
                    (order_id, backend_id))
                partner_id_found = context.env.cr.fetchone()
                print(partner_id_found)
                if partner_id_found:
                    partner_id = partner_id_found[0]
                    product_items = invoice['items']
                    invoice_line = []

                    # get order name
                    context.env.cr.execute(
                        """SELECT name FROM sale_order WHERE id in (SELECT odoo_id FROM magento_sale_order WHERE  external_id = %s AND backend_id = %s)""",
                        (order_id, backend_id))
                    order_name = context.env.cr.fetchall()[0][0]
                    sale_order_of_invoice = context.env['sale.order'].sudo().search([('name', '=', order_name)])
                    if 'shipping_amount' in invoice:
                        shipping_amount = invoice[
                            'shipping_amount']  # if =0 >> first invoice, and it has ship method, invoices after first invoice don't ship method
                    else:
                        shipping_amount = 0
                    if sale_order_of_invoice.carrier_id.id:
                        context.env.cr.execute(
                            """SELECT product_id FROM delivery_carrier WHERE id = %s""" % (
                                sale_order_of_invoice.carrier_id.id))
                        product_id_ship_method = context.env.cr.fetchone()
                        rec_product_ship_method = context.env['product.product'].sudo().search(
                            [('id', '=', product_id_ship_method)])
                        list_name_product = []
                    for product_item in product_items:
                        product_id = product_item['product_id']
                        default_code = product_item['sku']
                        quantity = product_item['qty']
                        price = product_item['price']
                        if 'tax_amount' in product_item:
                            if 'row_total' in product_item and 'row_total_incl_tax' in product_item:
                                total_price = product_item['row_total']
                                row_total_incl_tax = product_item['row_total_incl_tax']
                                tax_amount = round((row_total_incl_tax - total_price), 2)
                                for tax_per in self.get_array_tax_percent(context):
                                    if round(((tax_per * total_price) / 100), 2) == tax_amount:
                                        tax_percent = tax_per
                                        break
                                else:
                                    tax_percent = 0
                            else:
                                tax_percent = 0
                            # if tax_percent > 0:
                            #     record_tax = context.env['account.tax'].sudo().search([('amount', '=', tax_percent)])
                            #     if record_tax:
                            #         tax_code = record_tax[0].name
                            #         tax_product_id = context.env['product.template'].sudo().search(
                            #             [('default_code', '=', tax_code)])

                        context.env.cr.execute("""
                                                                          SELECT * FROM combine_id({backend_id},{amount},'{default_code}',{external_id})""".
                                               format(backend_id=backend_id, amount=tax_percent,
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
                                product_id = context.env.ref('magento2_connector.magento_sample_product_service').id
                            invoice_line.append(
                                (0, 0, {'name': product_item['name'], 'account_id': 18, 'product_id': product_id,
                                        'quantity': quantity,
                                        'price_unit': price, }))
                            list_name_product.append(product_item['name'])
                            # 'invoice_line_tax_ids': [(4, account_tax_id) if account_tax_id != '' else '']}))
                    if shipping_amount > 0:
                        if sale_order_of_invoice.carrier_id.id:
                            invoice_line.append((0, 0, {'name': rec_product_ship_method.name, 'account_id': 18,
                                                        'product_id': rec_product_ship_method.id,
                                                        'quantity': 1,
                                                        'price_unit': shipping_amount, }))
                            # 'invoice_line_tax_ids': rec_product_ship_method.taxes_id}))
                    if 'tax_amount' in invoice and invoice['tax_amount'] > 0:
                        origin_tax_amount = invoice['tax_amount']
                        tax_real_product_id = context.env.ref('magento2_connector.tax_real')
                        tax_fake_product_id = context.env.ref('magento2_connector.tax_fake')
                        tax_percent_id = context.env.ref('magento2_connector.tax_100')
                        invoice_line.append((0, 0, {'name': "Tax real", 'account_id': 18,
                                                    'product_id': tax_real_product_id.id,
                                                    'quantity': 1,
                                                    'name': str(list_name_product),
                                                    'price_unit': float(origin_tax_amount),
                                                    'invoice_line_tax_ids': [(4, tax_percent_id.id)]}))
                        invoice_line.append(
                            (0, 0, {'name': "To keep correct amount on Tax (for Accounting) and grant total",
                                    'account_id': 18,
                                    'product_id': tax_fake_product_id.id,
                                    'quantity': 1,
                                    'price_unit': -float(origin_tax_amount), }))
                    if 'discount_description' in invoice:
                        discount_amount = invoice['discount_amount']
                        discount_code = invoice['discount_description']
                        invoice_line_discount = context.env.ref('magento2_connector.discount_record')
                        invoice_line.append((0, 0, {'name': "Discount", 'account_id': 18,
                                                    'product_id': invoice_line_discount.id,
                                                    'quantity': 1,
                                                    'name': "Discount when use code " + str(discount_code),
                                                    'price_unit': discount_amount, }))

                    number = prefix + increment_id
                    array_odoo_invoices.append({
                        'partner_id': partner_id,
                        'currency_id': currency_id.id,
                        'type': 'out_invoice',
                        'state': state,
                        'number': number,
                        'move_name': number,
                        'reference': number,
                        'journal_id': journal_id,
                        'origin': order_name,
                        'invoice_line_ids': invoice_line if len(invoice_line) > 0 else '',
                        'is_magento_invoice': True
                    })

                    array_magento_invoices.append((invoice_id, backend_id, state))
                    print(array_magento_invoices)
                else:
                    print('cant find customer for magento sale order ' + str(order_id))

        if array_odoo_invoices and len(array_odoo_invoices) > 0:
            # invoice in odoo
            invoices = context.env['account.invoice'].sudo().create(array_odoo_invoices)
            invoice_ids = []

            # insert invoice in magento_account_invoice
            for invoice in invoices:
                invoice.action_move_create()
                invoice_ids.append((invoice.id,))

            magento_invoices_mapped_id = tuple(map(lambda x, y: x + y, array_magento_invoices, invoice_ids))
            if array_magento_invoices and len(array_magento_invoices) > 0:
                context.env.cr.execute(
                    """INSERT INTO magento_account_invoice (external_id, backend_id, state, odoo_id) VALUES {values}""".format(
                        values=", ".join(["%s"] * len(magento_invoices_mapped_id))),
                    tuple(magento_invoices_mapped_id, ))

            # check status invoice and update it.(because when you create invoice, invoice's state default is open)
            for invoice in invoices:
                magento_invoice = context.env['magento.account.invoice'].search(
                    [('odoo_id', '=', invoice.id), ('backend_id', '=', backend_id)])
                if magento_invoice.state == 'paid':
                    # update invoice to open and re-paid
                    # invoice.update({
                    #     'state': 'open'
                    # })
                    # # dien journal id da config trong magento backend
                    # account_payment = context.env['account.payment'].sudo().create({
                    #     'amount': invoice.amount_total,
                    #     'currency_id': invoice.currency_id.id,
                    #     'payment_date': invoice.date,
                    #     'journal_id': payment_journal,
                    #     'communication': invoice.number,
                    #     'invoice_ids': [(6, 0, [invoice.id])],
                    #     'payment_method_id': context.env.ref('payment.account_payment_method_electronic_in').id,
                    #     'payment_type': 'inbound',
                    #     'partner_type': 'customer',
                    #     'partner_id': invoice.partner_id.id,
                    # })
                    # context.env['account.payment'].sudo().browse(account_payment.id).action_validate_invoice_payment()
                    pass
                elif magento_invoice.state == 'cancel':
                    context.env.cr.execute("""UPDATE account_invoice SET state = %s WHERE id = %s """,
                                           ('cancel', magento_invoice.odoo_id.ids[0]))
                    print("" + str(backend_id) + str(invoice.id))
