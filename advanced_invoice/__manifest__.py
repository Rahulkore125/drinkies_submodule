# -*- coding: utf-8 -*-
{
    'name': "advanced_invoice",

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
    'version': '2.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'advanced_sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_invoice_inherit_view.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
    ],
}