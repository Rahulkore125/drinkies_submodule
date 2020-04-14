# -*- coding: utf-8 -*-
{
    'name': "advanced_sale",

    'summary': """Update sale flow according to flow of Drinkies""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '2.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'sale', 'delivery', 'mail', 'stock', 'sales_team', 'uom', 'stock_account', 'sale_coupon','advanced_stock'],

    # always loaded
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'data/sale_team_heineken_data.xml',
        'views/res_partner_view.xml',
        'views/sale_order_view.xml',
        'views/sale_hnk_report_view.xml',
        'views/stock_view.xml'
    ],
}