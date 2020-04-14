# -*- coding: UTF-8 -*-
# -*- coding: UTF-8 -*-

from odoo.exceptions import UserError
from odoo.http import request
from ..magento.rest import Client


class Product(Client):
    __slots__ = ()

    def list(self, current_page, page_size):
        return self.call('rest/V1/products',
                         'searchCriteria[currentPage]' + str(current_page) + '&searchCriteria[pageSize]=' + str(
                             page_size))

    def list_gt_updated_product(self, updated_at, condition):
        return self.call('rest/V1/products',
                         'searchCriteria[filter_groups][0][filters][0][field]=updated_at&'
                         'searchCriteria[filter_groups][0][filters][0][value]=' + str(updated_at) + '&'
                                                                                                    'searchCriteria[filter_groups][0][filters][0][condition_type]=gt&'
                                                                                                    'searchCriteria[filter_groups][1][filters][0][field]=type_id&'
                                                                                                    'searchCriteria[filter_groups][1][filters][0][value]=configurable&'
                                                                                                    'searchCriteria[filter_groups][1][filters][0][condition_type]=' + str(
                             condition))

    def list_product(self, page_size, current_page, type, condition):
        return self.call('rest/V1/products',
                         'searchCriteria[currentPage]=' + str(current_page) + '&'
                                                                              'searchCriteria[pageSize]=' + str(
                             page_size) + '&'
                                          'searchCriteria[filter_groups][0][filters][0][field]=type_id&'
                                          'searchCriteria[filter_groups][0][filters][0][value]=' + str(type) + '&'
                                                                                                               'searchCriteria[filter_groups][0][filters][0][condition_type]=' + str(
                             condition))

    def list_attribute_type_select(self):
        return self.call('rest/V1/products/attributes',
                         'searchCriteria[filterGroups][0][filters][0][field]=frontend_input&'
                         'searchCriteria[filterGroups][0][filters][0][value]=select')

    def list_categories(self):
        return self.call('rest/V1/categories', 'searchCriteria')

    def insert_configurable_product(self, products, backend_id, url, token, context=None):
        product_children = []
        odoo_product_template = []
        odoo_product_product_ids = []
        magento_product_product = []
        for product in products:
            # magento
            external_product_id = product['id']
            # product_type_magento = 'magento_'+str(product['type_id'])
            # check product neu co weight thi la comsumable, neu ko co weight la service
            custom_attributes = product['custom_attributes']
            description = ""
            for rec in custom_attributes:
                if rec['attribute_code'] == 'short_description':
                    description = rec['value']
                    description = BeautifulSoup(description).get_text()
                    break
            # odoo
            name = product['name']
            if 'price' in product:
                price = product['price']
            else:
                price = 0
            if 'weight' in product:
                weight = product['weight']
            else:
                weight = 0
            if weight > 0:
                product_type_magento = 'product'
            else:
                # todo
                product_type_magento = 'product'
            categories = []
            # add category
            categories = []
            if 'category_links' in product['extension_attributes']:
                magento_categories = product['extension_attributes']['category_links']
                list_magento_category = []
                for rec in magento_categories:
                    list_magento_category.append(rec['category_id'])
                total_category = context.env['magento.product.category'].search([('backend_id', '=', backend_id)])
                for cate in total_category:
                    if str(cate.external_id) in list_magento_category:
                        categories.append(cate.odoo_id.id)
            category = "1"
            unit_of_measure = "1"
            uom_po_id = "1"
            responsible_id = "1"
            sku = product['sku']
            sequence = '1'
            sale_ok = True
            purchase_ok = True
            if 'configurable_product_options' in product['extension_attributes']:
                configurable_product_options = product['extension_attributes']['configurable_product_options']
            else:
                configurable_product_options = False

            # magento product product
            # update
            magento_product = context.env['magento.product.product'].search(
                [('backend_id', '=', backend_id), ('external_id', '=', external_product_id)], limit=1)
            if len(magento_product.ids) > 0:
                pass
            else:
                attribute_ids = []
                if configurable_product_options and len(configurable_product_options) > 0:
                    for option in configurable_product_options:
                        context.env.cr.execute(
                            """SELECT odoo_id FROM magento_product_attribute WHERE backend_id=%s AND external_id = %s""" % (
                                backend_id, option['attribute_id']))
                        odoo_attribute_id = context.env.cr.fetchone()[0]
                        magento_attribute_values = []
                        for value in option['values']:
                            context.env.cr.execute(
                                """SELECT id FROM product_attribute_value WHERE attribute_id=%s AND magento_value = '%s'""" % (
                                    odoo_attribute_id, value['value_index']))
                            existing_product_attribute = context.env.cr.fetchone()
                            if existing_product_attribute:
                                value_index = existing_product_attribute[0]
                                magento_attribute_values.append(value_index)
                            else:
                                print(odoo_attribute_id)
                                print(value['value_index'])
                                # Magento has some orders contain some items which have deleted attributes
                                # todo
                                print('no product_attribute_value have attribute_id=' + str(
                                    odoo_attribute_id) + 'and magento_value=' + str(value['value_index']))
                        if odoo_attribute_id and len(magento_attribute_values):
                            # print(magento_attribute_values)
                            attribute_ids.append((0, 0, {'attribute_id': odoo_attribute_id,
                                                         'value_ids': [(6, 0, magento_attribute_values)]}))
                sku_existed = context.env['product.template'].search([('default_code', '=', sku)])
                if sku_existed:
                    sku_existed.write({
                        'name': name,
                        'default_code': sku,
                        'active': True,
                        'list_price': price,
                        'magento_sale_price': price,
                        'weight': weight,
                        'categ_id': category,
                        'categories': [((4, cate_id)) for cate_id in categories],
                        'uom_id': unit_of_measure,
                        'uom_po_id': uom_po_id,
                        'responsible_id': responsible_id,
                        'sequence': sequence,
                        'sale_ok': sale_ok,
                        'type': product_type_magento,
                        'magento_product_type': 'magento_' + str(product['type_id']),
                        'purchase_ok': purchase_ok,
                        'is_magento_product': True,
                        'description': description
                    })
                else:
                    odoo_product_template.append({
                        'name': name,
                        'default_code': sku,
                        'active': True,
                        'magento_sale_price': price,
                        'list_price': price,
                        'weight': weight,
                        'categ_id': category,
                        'categories': [((4, cate_id)) for cate_id in categories],
                        'uom_id': unit_of_measure,
                        'uom_po_id': uom_po_id,
                        'responsible_id': responsible_id,
                        'sequence': sequence,
                        'sale_ok': sale_ok,
                        'purchase_ok': purchase_ok,
                        'type': product_type_magento,
                        'magento_product_type': 'magento_' + str(product['type_id']),
                        'attribute_line_ids': attribute_ids,
                        'is_magento_product': True,
                        'description': description
                    })
                    extension_attributes = product['extension_attributes']
                    if 'configurable_product_links' in extension_attributes:
                        configurable_product_links = extension_attributes['configurable_product_links']
                        for product_link in configurable_product_links:
                            product_children.append(product_link)

                    magento_product_product.append((backend_id, external_product_id))
        # if odoo_product_template and len(odoo_product_template) > 0:
        #     product_template_ids = context.env['product.template'].create(odoo_product_template)
        if odoo_product_template and len(odoo_product_template) > 0:
            product_template_ids = context.env['product.template'].create(odoo_product_template)
            for product_tmpl_id in product_template_ids:
                for product_product_id in product_tmpl_id.product_variant_ids:
                    odoo_product_product_ids.append(product_product_id.id)

            if len(odoo_product_product_ids) == len(product_children):
                context.env.cr.execute(
                    """INSERT INTO magento_product_product(odoo_id, external_id, backend_id) VALUES {values}""".
                        format(values=", ".join(["%s"] * len(odoo_product_product_ids))),
                    tuple(
                        map(lambda x, y: (x,) + (y,) + (backend_id,), odoo_product_product_ids, product_children)))
            else:
                raise UserError(product['name'] + "len(odoo_product_product_ids) != len(product_children) " + str(
                    len(odoo_product_product_ids)) + '|' + str(len(product_children)))
        return 0

    def insert_not_configurable_product(self, products, backend_id, url, token, context=None):
        product_children = []
        odoo_product_template = []
        magento_product_product = []
        for product in products:
            product_exist = request.env['magento.product.product'].search([('external_id', '=', product['id'])])
            # kiem tra product nay da duoc pull ve hay chua
            if not len(product_exist) > 0:
                extension_attributes = product['extension_attributes']
                if 'configurable_product_links' in extension_attributes:
                    configurable_product_links = extension_attributes['configurable_product_links']
                    for product_link in configurable_product_links:
                        product_children.append(product_link)
                external_product_id = product['id']
                name = product['name']
                if 'price' in product:
                    price = product['price']
                else:
                    price = 0
                custom_attributes = product['custom_attributes']
                description = ""
                for rec in custom_attributes:
                    if rec['attribute_code'] == 'short_description':
                        description = rec['value']

                        break
                # add category
                categories = []
                if 'category_links' in product['extension_attributes']:
                    magento_categories = product['extension_attributes']['category_links']
                    list_magento_category = []
                    for rec in magento_categories:
                        list_magento_category.append(rec['category_id'])
                    total_category = context.env['magento.product.category'].search([('backend_id', '=', backend_id)])
                    for cate in total_category:
                        if str(cate.external_id) in list_magento_category:
                            categories.append(cate.odoo_id.id)

                category = "1"
                unit_of_measure = "1"
                uom_po_id = "1"
                responsible_id = "1"
                sku = product['sku']
                sequence = '1'
                sale_ok = True
                purchase_ok = True
                if 'weight' in product:
                    weight = product['weight']
                else:
                    weight = 0
                # todo
                if weight > 0:
                    magento_product_type = 'product'
                else:
                    magento_product_type = 'product'
                product_type_magento = 'magento_' + str(product['type_id'])
                # update
                sku_existed = context.env['product.template'].search([('default_code', '=', sku)])
                if sku_existed:
                    sku_existed.write({
                        'name': name,
                        'default_code': sku,
                        'active': True,
                        'list_price': price,
                        'magento_sale_price': price,
                        'weight': weight,
                        'categ_id': category,
                        'categories': [((4, cate_id)) for cate_id in categories],
                        'uom_id': unit_of_measure,
                        'uom_po_id': uom_po_id,
                        'responsible_id': responsible_id,
                        'sequence': sequence,
                        'sale_ok': sale_ok,
                        'type': magento_product_type,
                        'magento_product_type': product_type_magento,
                        'purchase_ok': purchase_ok,
                        'is_magento_product': True,
                        'description': description
                    })
                else:
                    magento_product = context.env['magento.product.product'].search(
                        [('backend_id', '=', backend_id), ('external_id', '=', external_product_id)], limit=1)
                    if magento_product:
                        # check if configurable product
                        if magento_product.odoo_id.product_tmpl_id.product_variant_count > 1:
                            parent_sku = magento_product.odoo_id.product_tmpl_id.default_code
                            magento_product.odoo_id.write(
                                {'magento_sale_price': price, 'default_code': sku,
                                 'magento_product_name': name})
                            magento_product.odoo_id.product_tmpl_id.write(
                                {'description': description, 'default_code': parent_sku}
                            )
                        else:
                            parent_sku = magento_product.odoo_id.product_tmpl_id.default_code
                            magento_product.odoo_id.write(
                                {'name': name, 'list_price': price, 'magento_sale_price': price,
                                 'default_code': sku})
                            magento_product.odoo_id.product_tmpl_id.write(
                                {'description': description, 'default_code': parent_sku}
                            )
                    else:
                        if not (external_product_id in product_children):
                            odoo_product_template.append({
                                'name': name,
                                'default_code': sku,
                                'active': True,
                                'list_price': price,
                                'magento_sale_price': price,
                                'weight': weight,
                                'categ_id': category,
                                'categories': [((4, cate_id)) for cate_id in categories],
                                'uom_id': unit_of_measure,
                                'uom_po_id': uom_po_id,
                                'responsible_id': responsible_id,
                                'sequence': sequence,
                                'sale_ok': sale_ok,
                                'type': magento_product_type,
                                'magento_product_type': product_type_magento,
                                'purchase_ok': purchase_ok,
                                'is_magento_product': True,
                                'description': description,
                                'is_heineken_product': True
                            })
                        magento_product_product.append((external_product_id, backend_id))
        if odoo_product_template and len(odoo_product_template) > 0:
            product_template_ids = context.env['product.template'].create(odoo_product_template)
            product_product_ids = []
            for product_tmpl_id in product_template_ids:
                if len(product_tmpl_id.product_variant_ids) > 0:
                    product_product_ids.append(product_tmpl_id.product_variant_ids[0].id)
            if len(product_product_ids) == len(magento_product_product):
                context.env.cr.execute(
                    """INSERT INTO magento_product_product(odoo_id, external_id, backend_id) VALUES {values}""".
                        format(values=", ".join(["%s"] * len(product_product_ids))),
                    tuple(map(lambda x, y: (x,) + y, product_product_ids, magento_product_product)))
            else:
                raise UserError("Error,Please try again!")

        return 0

    def insert_product_attribute(self, attributes, backend_id, context=None):
        product_attribute = []
        magento_product_attribute = []
        result = []
        # prepare new attribute and attribute values
        new_product_attributes = []
        new_product_attribute_values = []

        for attribute in attributes:
            default_frontend_label = attribute['default_frontend_label']
            attribute_code = attribute['attribute_code']  # name
            attribute_id = attribute['attribute_id']
            frontend_input = attribute['frontend_input']  # type
            options = attribute['options']  # product value
            all_options = []
            all_option_values = []
            for option in options:
                if option['label'] not in all_option_values:
                    all_options.append(option)
                    all_option_values.append(option['label'])
                else:
                    option['label'] = option['label'] + '_' + option['value']
                    all_options.append(option)
                    all_option_values.append(option['label'])
            new_product_attributes_item = {
                'backend_id': backend_id,
                'external_id': attribute_id,
                'name': attribute_code,
                'type': frontend_input,
                'create_variant': 'always'
            }
            new_product_attributes.append(new_product_attributes_item)
            # insert and update attribute
            current_attribute = context.env['product.attribute'].sudo().search(
                [('backend_id', '=', backend_id), ('external_id', '=', attribute_id)])
            if len(current_attribute.ids) > 0:
                current_attribute.write({
                    'backend_id': backend_id,
                    'external_id': attribute_id,
                    'name': attribute_code,
                })
            else:
                context.env['product.attribute'].sudo().create(new_product_attributes_item)

            for option in all_options:
                new_product_attribute_values.append({
                    'name': option['label'],
                    'magento_value': option['value'],
                    'backend_id': backend_id,
                    'attribute_id_external_id': attribute_id,
                })
            magento_product_attribute.append((backend_id, attribute_id))
        # list all existing product attribute values, remove redundant
        existing_product_attribute_values = context.env['product.attribute.value'].sudo().search(
            [('backend_id', '=', backend_id)])
        for existing_attribute_value in existing_product_attribute_values:
            need_to_remove = True
            for e in new_product_attribute_values:
                if existing_attribute_value.backend_id.id == e[
                    'backend_id'] and existing_attribute_value.attribute_id_external_id == e[
                    'attribute_id_external_id'] and existing_attribute_value.magento_value == e[
                    'magento_value']:
                    need_to_remove = False
            if need_to_remove:
                context.env['product.attribute.value'].sudo().search([('backend_id', '=', backend_id), (
                    'attribute_id_external_id', '=', existing_attribute_value.attribute_id_external_id), (
                                                                          'magento_value', '=',
                                                                          existing_attribute_value.magento_value)]).unlink()
        # insert or update attribute_values

        # get all attribute in Odoo
        all_attribute = context.env['product.attribute'].sudo().search([('backend_id', '=', backend_id)])
        for new_product_attribute_value in new_product_attribute_values:
            existing_attribute_value = context.env['product.attribute.value'].sudo().search([
                ('backend_id', '=', backend_id), (
                    'attribute_id_external_id', '=', new_product_attribute_value['attribute_id_external_id']), (
                    'magento_value', '=', new_product_attribute_value['magento_value'])])
            # if exist update
            if len(existing_attribute_value.ids) > 0:
                existing_attribute_value.update(new_product_attribute_value)
            else:
                # if not insert
                for attribute in all_attribute:
                    if attribute.external_id == new_product_attribute_value['attribute_id_external_id']:
                        context.env['product.attribute.value'].sudo().create({
                            'name': new_product_attribute_value['name'],
                            'magento_value': new_product_attribute_value['magento_value'],
                            'backend_id': new_product_attribute_value['backend_id'],
                            'attribute_id_external_id': new_product_attribute_value['attribute_id_external_id'],
                            'attribute_id': attribute.id
                        })
        # update attribute values
        result = context.env['product.attribute'].sudo().search([('backend_id', '!=', False)])
        product_attribute_ids = []
        for res in result:
            product_attribute_ids.append((res.id,))
        magento_product_attribute_mapped = tuple(
            map(lambda x, y: x + y, product_attribute_ids, magento_product_attribute))
        if magento_product_attribute_mapped and len(magento_product_attribute_mapped) > 0:
            # search if exist
            query = "SELECT odoo_id, backend_id, external_id FROM magento_product_attribute"
            context.env.cr.execute(query)
            exist_data = context.env.cr.fetchall()
            if exist_data:
                list_fixed = []
                for i in magento_product_attribute_mapped:
                    exist = False
                    for j in exist_data:
                        if i[1] == j[1] and i[2] == j[2]:
                            exist = True
                    if not exist:
                        list_fixed.append(i)
                magento_product_attribute_mapped = list_fixed
            if len(magento_product_attribute_mapped) > 0:
                context.env.cr.execute(
                    """INSERT INTO magento_product_attribute (odoo_id, backend_id, external_id) VALUES {values}""".format(
                        values=", ".join(["%s"] * len(magento_product_attribute_mapped))),
                    tuple(magento_product_attribute_mapped))

    # handle sync categories from magento

    def insert_odoo_product_category(self, categories, next_odoo_id_product_category,
                                     next_magento_id_product_category, backend_id, context=None):
        queue = []  # hang doi duyet cay json
        odoo_product_category_queue = []  # hang doi luu odoo category
        magento_product_category_arrray = []  # mang luu ket qua magento_product_category
        magento_product_category_queue = []  # hang doi luu magento categpry

        # them cac gia tri cua phan tu goc cay json vao cac mang
        # odoo
        odoo_id = next_odoo_id_product_category
        name = categories['name']
        odoo_parent_id = None
        # magento
        magento_id = next_magento_id_product_category
        magento_product_catgory_name = categories['name']
        external_id = categories['id']
        magento_parent_id = None
        product_count = categories['product_count']
        context.env['product.category'].create({
            'name': name,
            'parent_id': odoo_parent_id,
        })
        odoo_product_category_queue.append((odoo_id, name, odoo_parent_id))

        magento_product_category_arrray.append(
            (odoo_id, external_id, magento_parent_id, product_count, backend_id, magento_product_catgory_name))
        magento_product_category_queue.append((magento_id,))

        # duyet cay json
        queue.append(categories)
        # neu chua duyet het tuc la van con phan tu trong hang doi, len(queue) > 0
        while len(queue) != 0:
            # thuat toan thuc hien duyet cay theo tung level,
            # them nut goc vao hang doi, them du lieu cua nut goc va mang ket qua
            # lay nut goc ra roi them cac con cua nut vao hang doi, them du lieu cac con vao mang ket qua
            # lap lai tuong tu nhu nut goc voi nua dau tien cua hang doi cho den khi duyet het duoc cay json
            # mang odoo_product_category_queue va magento_product_category_queue de chuan hoa du lieu tu cay json trc khi cho vao mang ket qua_
            for e in queue[0]['children_data']:
                # odoo
                next_odoo_id_product_category += 1
                odoo_id = next_odoo_id_product_category
                name = e['name']
                odoo_parent_id = odoo_product_category_queue[0][0]  # lay ra odoo_id cua cha
                # magento
                next_magento_id_product_category += 1
                magento_id = next_magento_id_product_category
                magento_product_catgory_name = e['name']
                external_id = e['id']
                product_count = e['product_count']
                magento_parent_id = magento_product_category_queue[0][0]

                context.env['product.category'].create({
                    'name': name,
                    'parent_id': odoo_parent_id,
                })
                magento_product_category_arrray.append(
                    (odoo_id, external_id, magento_parent_id, product_count, backend_id, magento_product_catgory_name))

                odoo_product_category_queue.append((odoo_id, name, odoo_parent_id))
                magento_product_category_queue.append((magento_id,))
                queue.append(e)
            queue.pop(0)
            odoo_product_category_queue.pop(0)
            magento_product_category_queue.pop(0)

        return magento_product_category_arrray

    def insert_product_category(self, categories, backend_id, context=None):
        # get odoo next id
        context.env.cr.execute("SELECT nextval(pg_get_serial_sequence('product_category','id'))")
        odoo_ids = context.env.cr.fetchall()
        odoo_id = odoo_ids[0][0] + 1
        # get magento next id
        context.env.cr.execute("SELECT nextval(pg_get_serial_sequence('magento_product_category','id'))")
        magento_ids = context.env.cr.fetchall()
        magento_id = magento_ids[0][0] + 1
        magento_product_category_array = self.insert_odoo_product_category(categories, odoo_id, magento_id,
                                                                           backend_id, context)
        if magento_product_category_array and len(magento_product_category_array) > 0:
            context.env.cr.execute("""INSERT INTO magento_product_category(odoo_id,external_id,magento_parent_id,product_count,backend_id,name)
                                         VALUES {values}""".format(
                values=", ".join(["%s"] * len(magento_product_category_array))), tuple(magento_product_category_array))

    def insert_product_category_odoo_in_json(self, result, context=None):
        context.env.cr.execute("SELECT external_id,name FROM magento_product_category")
        categories = context.env.cr.fetchall()
        for e in categories:
            result[str(e[0])] = e[1]

    def get_product_category_magento(self, categories, result):
        for e in categories['children_data']:
            result.append(e)
            self.get_product_category_magento(e, result)

    def get_category_need_update_or_insert(self, categories, context=None):
        product_category_odoo_json = {}
        product_category_magento = []

        product_category_create = []
        product_category_update = []

        product_category_magento.append(categories)
        self.get_product_category_magento(categories, product_category_magento)
        self.insert_product_category_odoo_in_json(product_category_odoo_json, context)

        for e in product_category_magento:
            if str(e['id']) not in product_category_odoo_json:
                product_category_create.append(e)
            else:
                if product_category_odoo_json[str(e['id'])] != e['name']:
                    product_category_update.append(e)
        return product_category_create, product_category_update

    def insert_new_product_category(self, category):
        pass

    def update_product_category(self, category):
        external_id = category['id']
        name = category['name']
        magento_product_category = request.env['magento.product.category'].sudo().search(
            [('external_id', '=', external_id)])
        magento_product_category.write({
            'name': name
        })
        odoo_id = magento_product_category.odoo_id._ids[0]
        odoo_product_category = request.env['product.category'].search([('id', '=', odoo_id)])
        odoo_product_category.write({
            'name': name
        })

    def create_product_category(self, category, backend_id):
        external_id = category['id']
        external_parent_id = category['parent_id']
        name = category['name']

        magento_product_category = request.env['magento.product.category'].sudo().search(
            [('external_id', '=', external_parent_id)])
        odoo_parent_id = magento_product_category.odoo_id._ids[0]
        odoo_product_category = request.env['product.category'].create({
            'name': name,
            'parent_id': odoo_parent_id
        })
        odoo_id = odoo_product_category.id
        magento_parent_id = magento_product_category.id
        request.env['magento.product.category'].sudo().create({
            'external_id': external_id,
            'magento_parent_id': magento_parent_id,
            'odoo_id': odoo_id,
            'backend_id': backend_id,
            'name': name
        })

    def update_product_categories(self, categories, backend_id, context=None):
        product_category_create, product_category_update = self.get_category_need_update_or_insert(categories, context)
        for e in product_category_update:
            self.update_product_category(e)
        for e in product_category_create:
            self.create_product_category(e, backend_id)
