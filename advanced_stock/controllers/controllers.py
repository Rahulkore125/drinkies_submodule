# -*- coding: utf-8 -*-
from odoo import http

# class AdvancedStock(http.Controller):
#     @http.route('/advanced_stock/advanced_stock/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/advanced_stock/advanced_stock/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('advanced_stock.listing', {
#             'root': '/advanced_stock/advanced_stock',
#             'objects': http.request.env['advanced_stock.advanced_stock'].search([]),
#         })

#     @http.route('/advanced_stock/advanced_stock/objects/<model("advanced_stock.advanced_stock"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('advanced_stock.object', {
#             'object': obj
#         })