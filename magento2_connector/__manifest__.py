# -*- coding: utf-8 -*-
{
    'name': "Magento Connector",

    'summary': """
        Pull orders from Drinkies to Odoo""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Magento Connector',
    'version': '2.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'sale', 'sale_management', 'product', 'payment', 'delivery','sale_coupon', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/sale/sale_views.xml',
        'views/product/product.xml',
        'views/product/categories.xml',
        # 'views/config/res_config_settings_views.xml',
        'views/config/magento_instance.xml',
        'views/invoice/invoice_view.xml',
        'views/invoice/invoice_magento_filter_view.xml',
        'views/product/product_magento_filter_view.xml',
        'views/sale/sale_order_magento_filter_view.xml',
        'views/product/product_attributes_view.xml',
        'views/product/product_template.xml',
        'views/location/stock_location.xml',
        'views/config/magento_operation.xml',
        'views/dashboard/website.xml',
        'views/dashboard/store.xml',
        'views/dashboard/storeview.xml',
        'views/dashboard/dashboard_view.xml',

        # data
        'data/product_scheduler.xml',
        'data/customer_scheduler.xml',
        'data/customer_guest.xml',
        'data/sale_order_scheduler.xml',
        'data/invoice_scheduler.xml',
        'data/shipping_method_product.xml',
        'data/shipping_method.xml',
        'data/sample_data.xml',
        'data/tax_data.xml',

        #wizard
        'wizard/popup_dialog_view.xml'

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
