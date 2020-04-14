# -*- coding: UTF-8 -*-
from ..magento.rest import Client


def get_country_id(code, context=None):
    res_country = context.env['res.country'].search([('code', '=', code)], limit=1)
    return res_country.id


def get_state_id(country_id, region, region_code, context=None):
    if context is not None:
        state_id = context.env['res.country.state'].search(
            [('country_id', '=', country_id), ('code', '=', region_code), ('name', '=', region)], limit=1)
        return state_id.id
    return None


class Customer(Client):
    __slots__ = ()

    def list_all(self):

        return self.call('rest/V1/customers/search', 'searchCriteria')

    def list(self, pageSize, currentPage):

        return self.call('rest/V1/customers/search',
                         'searchCriteria[currentPage]=' + str(currentPage) + '&searchCriteria[pageSize]=' + str(
                             pageSize))

    def list_gt_updated_at(self, updated_at):
        return self.call('rest/V1/customers/search',
                         'searchCriteria[filter_groups][0][filters][0][field]=updated_at&searchCriteria[filter_groups][0][filters][0][value]=' + str(
                             updated_at) + '&searchCriteria[filter_groups][0][filters][0][condition_type]=gt')

    def insert(self, customers, backend_id, url, token, context=None):
        array_address = []
        array_customer = []
        print(array_customer)
        for customer in customers:
            magento_customer_id = customer['id']
            name = customer['firstname'] + " " + customer['lastname']
            email = customer['email']
            # default_billing_id = int(customer['default_billing'])

            # magento
            website_id = self.adapter_magento_id('magento_website', backend_id, customer['website_id'], context)
            storeview_id = self.adapter_magento_id('magento_storeview', backend_id, customer['store_id'], context)
            group_id = self.adapter_magento_id('magento_res_partner_category', backend_id, customer['group_id'],
                                               context)
            res_partner = context.env['magento.res.partner'].search(
                [('backend_id', '=', backend_id), ('external_id', '=', magento_customer_id)], limit=1)
            rec_email_existed = context.env['magento.res.partner'].search(
                [('email', '=', email), ('active', '=', True)])
            rec_email_existed = sorted(rec_email_existed, key=lambda rec: -rec['id'])
            # update
            if rec_email_existed:
                # trong truong hop rec_email_existed >  2 record : thi lay cai cuoi cung va update no, xoa tat ca cac cai con lai
                old_partner_parent = context.env['res.partner'].search(
                    [('id', '=', rec_email_existed[0].odoo_id.id), ('active', '=', True)])
                for record in rec_email_existed:
                    old_partner_parent_orther = context.env['res.partner'].search(
                        [('id', '=', record.odoo_id.id), ('active', '=', True)])
                    if old_partner_parent_orther.id != old_partner_parent.id:
                        old_partner_parent_orther.update({
                            'active': False
                        })
                rec_email_existed[0].update({
                    'external_id': magento_customer_id,
                    'website_id': website_id,
                    'storeview_id': storeview_id,
                    'name': name,
                    'display_name': name,
                    'email': email,
                    'group_id': group_id
                })
                # xoa tat ca cac partner co email bi trung con lai
                for email_existed in rec_email_existed:
                    old_partner_child = context.env['res.partner'].search(
                        [('id', '!=', email_existed.odoo_id.id), ('email', '=', email), ('active', '=', True)])
                    for partner in old_partner_child:
                        # cap nhat sale order co lien quan, dinh vs partner o tren
                        # sale_orders = context.env['magento.sale.order'].search([('partner_id', '=', partner.id)])
                        # for order in sale_orders:
                        #     order.update({
                        #         'partner_id': old_partner_parent.id
                        #     })
                        partner.update({
                            'active': False
                        })
                # update new address if new customer have address
                if customer['addresses'] and len(customer['addresses']) > 0:
                    # first address
                    new_address = customer['addresses'][0]
                    new_street = new_address['street'][0]
                    # first_telephone = first_address['telephone']
                    if 'postcode' in new_address:
                        new_postcode = new_address['postcode']
                    else:
                        new_postcode = ""
                    new_city = new_address['city']
                    new_country_id = get_country_id(new_address['country_id'], context)
                    new_state_id = False
                    if new_country_id:
                        new_state_id = get_state_id(new_country_id, new_address['region']['region'],
                                                    new_address['region']['region_code'],
                                                    context)
                    for partner in old_partner_parent:
                        partner.update({
                            'magento_customer_id': magento_customer_id,
                            'magento_id': magento_customer_id,
                            'street': new_street,
                            'zip': new_postcode,
                            'city': new_city,
                            'state_id': new_state_id,
                            'country_id': new_country_id
                        })
                else:
                    for partner in old_partner_parent:
                        partner.update({
                            'magento_customer_id': magento_customer_id,
                            'magento_id': magento_customer_id,
                            'street': False,
                            'zip': False,
                            'city': False,
                            'state_id': False,
                            'country_id': False
                        })
                res_partner = context.env['magento.res.partner'].search(
                    [('backend_id', '=', backend_id), ('external_id', '=', magento_customer_id)], limit=1)
            else:
                res_partner = context.env['magento.res.partner'].search(
                    [('backend_id', '=', backend_id), ('external_id', '=', magento_customer_id)], limit=1)
                if res_partner:
                    res_partner.write({
                        'website_id': website_id,
                        'storeview_id': storeview_id,
                        'name': name,
                        'display_name': name,
                        'email': email,
                        'group_id': group_id
                    })
                else:
                    if customer['addresses'] and len(customer['addresses']) > 0:
                        # first address
                        first_address = customer['addresses'][0]
                        first_street = first_address['street'][0]
                        # first_telephone = first_address['telephone']
                        if 'postcode' in first_address:
                            first_postcode = first_address['postcode']
                        else:
                            first_postcode = ""
                        first_city = first_address['city']
                        first_country_id = get_country_id(first_address['country_id'], context)
                        first_state_id = False
                        if first_country_id:
                            first_state_id = get_state_id(first_country_id, first_address['region']['region'],
                                                          first_address['region']['region_code'],
                                                          context)
                            # name, display_name, street, zip, city, state_id, country_id, email,
                        if first_state_id:
                            array_address.append((name, name, first_street, first_postcode, first_city, first_state_id,
                                                  first_country_id, email, None, True, True, magento_customer_id,
                                                  magento_customer_id, None, backend_id, True))
                        else:
                            array_address.append((name, name, first_street, first_postcode, first_city, None,
                                                  first_country_id, email, None, True, True, magento_customer_id,
                                                  magento_customer_id, None, backend_id, True))
                        array_customer.append((website_id, storeview_id, group_id))
                    else:
                        array_address.append((name, name, None, None, None, None,
                                              None, email, None, True, True, magento_customer_id,
                                              magento_customer_id, None, backend_id, True))
                        array_customer.append((website_id, storeview_id, group_id))
            addresses = customer['addresses']
            for address in addresses:
                address_id = address['id']
                address_name = address['firstname'] + " " + address['lastname']
                street = address['street'][0]
                telephone = address['telephone']
                if 'postcode' in address:
                    postcode = address['postcode']
                else:
                    postcode = ""
                city = address['city']
                country_id = get_country_id(address['country_id'], context)
                state_id = None
                if country_id:
                    state_id = get_state_id(country_id, address['region']['region'], address['region']['region_code'],
                                            context)

                # magento_id and magento_customer_id are id of customer default_billing
                # magento_id = magento_customer_id if address['id'] == default_billing_id else None
                if res_partner:
                    # check existed of address_id
                    context.env.cr.execute(
                        """SELECT id FROM res_partner WHERE magento_address_id=%s AND backend_id =%s""",
                        (address_id, backend_id))
                    record_contain_address = context.env.cr.fetchall()
                    if record_contain_address:
                        if state_id:
                            context.env.cr.execute(
                                """UPDATE res_partner SET name= %s , street= %s, phone=%s, zip=%s, city=%s, state_id=%s, country_id=%s WHERE magento_address_id = %s AND backend_id=%s""",
                                (address_name, street, telephone, postcode, city, state_id, country_id, address_id,
                                 backend_id))
                        else:
                            context.env.cr.execute(
                                """UPDATE res_partner SET name= %s , street= %s, phone=%s, zip=%s, city=%s, country_id=%s WHERE magento_address_id = %s AND backend_id=%s""",
                                (address_name, street, telephone, postcode, city, country_id, address_id, backend_id))
                    else:
                        if state_id:
                            context.env.cr.execute(
                                """INSERT INTO res_partner (name, street,zip,city,state_id,country_id, email,phone, active, customer, magento_id, magento_customer_id, magento_address_id, backend_id, is_from_magento) VALUES (%s,%s,%s,%s,%s, %s,%s, %s, %s, %s, %s, %s, %s,%s, %s)""",
                                (name, street, postcode, city, state_id, country_id, email, telephone, True, True,
                                 magento_customer_id,
                                 magento_customer_id, address_id, backend_id, True))
                        else:
                            context.env.cr.execute(
                                """INSERT INTO res_partner (name, street,zip,city,country_id, email,phone, active, customer, magento_id, magento_customer_id, magento_address_id, backend_id, is_from_magento) VALUES (%s,%s,%s,%s, %s,%s, %s, %s, %s, %s, %s, %s,%s, %s)""",
                                (name, street, postcode, city, country_id, email, telephone, True, True,
                                 magento_customer_id,
                                 magento_customer_id, address_id, backend_id, True))
                        # get id of new partner (has new address)
                        context.env.cr.execute(
                            """SELECT id FROM res_partner WHERE magento_address_id=%s AND backend_id =%s""",
                            (address_id, backend_id))
                        magento_partner_new_id = context.env.cr.fetchone()
                        # get_id of mangeto_parter_id of new partner (has new address)
                        context.env.cr.execute(
                            """SELECT id FROM magento_res_partner WHERE external_id = %s and backend_id =%s""",
                            (magento_customer_id, backend_id))
                        magento_partner_odoo_id = context.env.cr.fetchone()
                        # create new address for new partner (for customer existed)
                        context.env.cr.execute(
                            """INSERT INTO magento_address (odoo_id,magento_partner_id,backend_id) VALUES (%s,%s,%s)""",
                            (magento_partner_new_id, magento_partner_odoo_id, backend_id))

                else:
                    if not state_id:
                        addr = (
                            address_name, address_name, street, postcode, city, None, country_id, email, telephone,
                            True,
                            True, None, magento_customer_id, address_id, backend_id, True)
                    else:
                        addr = (
                            address_name, address_name, street, postcode, city, state_id, country_id, email, telephone,
                            True,
                            True, None, magento_customer_id, address_id, backend_id, True)
                    array_address.append(addr)
                    array_customer.append((website_id, storeview_id, group_id))
            # delete address if delete address on magento
            context.env.cr.execute(
                """SELECT magento_address_id FROM res_partner WHERE magento_customer_id = %s""" % magento_customer_id)
            list_address_old = context.env.cr.fetchall()
            list_magento_address_old = []
            for magento_add in list_address_old:
                list_magento_address_old.append(magento_add[0])
            list_address_current = []
            for add in addresses:
                list_address_current.append(add['id'])
            for magento_address_id in list_magento_address_old:
                if (magento_address_id not in list_address_current) and magento_address_id != None:
                    context.env.cr.execute(
                        """DELETE FROM res_partner WHERE magento_address_id = %s""" % magento_address_id)

        if array_address:
            query = """
                        INSERT INTO res_partner (name, display_name, street,zip,city,state_id,country_id, email,phone, active, customer, magento_id, magento_customer_id, magento_address_id, backend_id, is_from_magento) VALUES {values} RETURNING id, magento_id, magento_customer_id, magento_address_id
                    """.format(values=", ".join(["%s"] * len(array_address)))
            context.env.cr.execute(query, tuple(array_address))
            arr_ids = context.env.cr.fetchall()  # handling magento_res_partner
            handling_address = []
            magento_res_partner = []

            for i in range(len(arr_ids)):
                if not arr_ids[i][1]:
                    handling_address.append(arr_ids[i])
                else:
                    arr_ids[i] = arr_ids[i] + array_customer[i] + (backend_id,)
                    # delete element 2,3 (magento_customer_id, address_id)
                    magento_res_partner.append(arr_ids[i][: 2] + arr_ids[i][3 + 1:])
            # 2 'external_id': magento_id,
            # 5 'backend_id': backend_id,
            # 1 'odoo_id': odoo_id,
            # 4 'store _id'
            # 3 'website_id': self.adapter_magento_id('magento.website', backend_id, website_id),
            # 'group_id': self.adapter_magento_id('magento.res.partner.category', backend_id, group_id)
            if magento_res_partner:
                context.env.cr.execute(
                    """ INSERT INTO magento_res_partner (odoo_id, external_id, website_id,storeview_id,group_id,backend_id) VALUES {values} RETURNING id, backend_id, external_id""".
                        format(values=", ".join(["%s"] * len(magento_res_partner))), tuple(magento_res_partner))
                res_partner = context.env.cr.fetchall()

                result = []
                for i in range(len(res_partner)):
                    for j in range(len(handling_address)):
                        if res_partner[i][2] == handling_address[j][2]:
                            result.append((handling_address[j][0], handling_address[j][3], res_partner[i][1],
                                           res_partner[i][0]))  # odoo_id, external_id,backend_id,magento_partner_id
                if len(result) > 0:
                    context.env.cr.execute(
                        """ INSERT INTO magento_address (odoo_id,external_id, backend_id, magento_partner_id) VALUES {values}""".
                            format(values=", ".join(["%s"] * len(result))), tuple(result))

        return 0

    def insert_customer_not_loggin(self, customers):
        pass

    def insert_conflict(self, customeres):
        pass

    def create(self, data):

        return int(self.call('customer.create', [data]))

    def info(self, id, attributes=None):

        if attributes:
            return self.call('customer.info', [id, attributes])
        else:
            return self.call('customer.info', [id])

    def update(self, id, data):

        return self.call('customer.update', [id, data])

    def delete(self, id):

        return self.call('customer.delete', [id])


class CustomerGroup(Client):
    """
    Customer Group API to connect to magento
    """
    __slots__ = ()

    def list_all(self):
        return self.call('rest/V1/customerGroups/search', 'searchCriteria')

    def list(self, currentPage, pageSize):
        return self.call('rest/V1/customerGroups/search',
                         'searchCriteria[currentPage]=' + str(currentPage) + '&searchCriteria[pageSize]=' + str(
                             pageSize))

    def insert(self, customer_groups, url, token, backend_id, context=None):
        uid = 1
        customer_groups_items = customer_groups['items']
        customer_groups_arr = []
        customer_groups_ids = []
        if len(customer_groups_items) > 0:
            for customer_group in customer_groups_items:
                magento_res_partner_category_id = context.env['magento.res.partner.category'].search(
                    [('backend_id', '=', backend_id), ('external_id', '=', customer_group['id'])], limit=1)
                if magento_res_partner_category_id:
                    pass
                else:
                    customer_groups_arr.append((customer_group['code'], 0, True, uid, uid))
                    customer_groups_ids.append((customer_group['id'],))
            if customer_groups_arr and len(customer_groups_arr) > 0:
                context.env.cr.execute("""INSERT INTO res_partner_category (name, color, active,create_uid,write_uid) VALUES {values} RETURNING id,{backend_id}
                                                   """.format(backend_id=backend_id,
                                                              values=", ".join(["%s"] * len(customer_groups_arr))),
                                       tuple(customer_groups_arr))

                odoo_ids = context.env.cr.fetchall()

                magento_res_partner_category = tuple(map(lambda x, y: x + y, odoo_ids, customer_groups_ids))

                if odoo_ids and len(odoo_ids) > 0:
                    context.env.cr.execute(
                        """INSERT INTO magento_res_partner_category(odoo_id, backend_id, external_id) VALUES {values}"""
                            .format(values=", ".join(["%s"] * len(magento_res_partner_category))),
                        tuple(magento_res_partner_category))

        return 0


class CustomerAddress(Client):
    """
    Customer Address API
    """
    __slots__ = ()

    def list(self, customer_id):
        """
        Retreive list of customer Addresses

        :param customer_id: ID of customer whose address needs to be fetched
        :return: List of dictionaries of matching records
        """
        return self.call('customer_address.list', [customer_id])

    def billing_address(self, customerId):
        return self.call('rest/V1/customers/' + str(customerId) + '/billingAddress', '')

    def shipping_address(self, customerId):
        return self.call('rest/V1/customers/' + str(customerId) + '/shippingAddress', '')

    def create(self, customer_id, data):
        """
        Create a customer using the given data

        :param customer_id: ID of customer, whose address is being added
        :param data: Dictionary of values (country, zip, city, etc...)
        :return: Integer ID of new record
        """
        return int(self.call('customer_address.create', [customer_id, data]))

    def info(self, id):
        """
        Retrieve customer data

        :param id: ID of customer
        """
        return self.call('customer_address.info', [id])

    def update(self, id, data):
        """
        Update a customer address using the given data

        :param id: ID of the customer address record to modify
        :param data: Dictionary of values
        :return: Boolean
        """
        return self.call('customer_address.update', [id, data])

    def delete(self, id):
        """
        Delete a customer address

        :param id: ID of address to delete
        :return: Boolean
        """
        return self.call('customer_address.delete', [id])
