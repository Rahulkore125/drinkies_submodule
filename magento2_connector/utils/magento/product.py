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
                                                                                                    'searchCriteria[filter_groups][0][filters][0][condition_type]=gteq&'
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
                        # 'uom_id': unit_of_measure,
                        # 'uom_po_id': uom_po_id,
                        'responsible_id': responsible_id,
                        'sequence': sequence,
                        'sale_ok': sale_ok,
                        'type': product_type_magento,
                        'magento_product_type': 'magento_' + str(product['type_id']),
                        'purchase_ok': purchase_ok,
                        'is_magento_product': True,
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
        if len(products) > 0:
            for product in products:
                if 'id' in product:
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
                        # add category
                        categories = []
                        if 'category_links' in product['extension_attributes']:
                            magento_categories = product['extension_attributes']['category_links']
                            list_magento_category = []
                            for rec in magento_categories:
                                list_magento_category.append(rec['category_id'])
                            total_category = context.env['magento.product.category'].search(
                                [('backend_id', '=', backend_id)])
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
                                # 'uom_id': unit_of_measure,
                                # 'uom_po_id': uom_po_id,
                                'responsible_id': responsible_id,
                                'sequence': sequence,
                                'sale_ok': sale_ok,
                                'type': magento_product_type,
                                'magento_product_type': product_type_magento,
                                'purchase_ok': purchase_ok,
                                'is_magento_product': True,
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
                                        { 'default_code': parent_sku}
                                    )
                                else:
                                    parent_sku = magento_product.odoo_id.product_tmpl_id.default_code
                                    magento_product.odoo_id.write(
                                        {'name': name, 'list_price': price, 'magento_sale_price': price,
                                         'default_code': sku})
                                    magento_product.odoo_id.product_tmpl_id.write(
                                        {'default_code': parent_sku}
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
