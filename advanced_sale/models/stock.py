from datetime import date, datetime
from ...magento2_connector.utils.magento.rest import Client
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo import tools, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    date_done_delivery = fields.Date()
    is_return_picking = fields.Boolean(default=False)
    has_return_picking = fields.Boolean(default=False)
    date_return = fields.Date()


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        for wizard in self:
            new_picking_id, pick_type_id = super(StockReturnPicking, wizard)._create_returns()
            # Override the context to disable all the potential filters that could have been set previously
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
        for move_line in picking.move_lines:
            move_line.quantity_done = move_line.product_uom_qty
        picking.action_done()
        picking.is_return_picking = True

        picking.date_return = date.today()

        origin_picking = self.env['stock.picking'].search(
            [('id', '=', wizard.picking_id.id)])
        origin_picking.has_return_picking = True

        self.env.cr.execute(
            """UPDATE sale_order SET state = %s WHERE id = %s""", ('cancel', picking.sale_id.id))

        action = self.env['sale.order'].browse(picking.sale_id.id).action_view_delivery()

        for e in picking.move_ids_without_package:
            if e.product_id.product_tmpl_id.multiple_sku_one_stock:
                stock_quant = self.env['stock.quant'].search(
                    [('location_id', '=', picking.location_dest_id.id),
                     ('product_id', '=', e.product_id.product_tmpl_id.variant_manage_stock.id)])

                stock_quant.sudo().write({
                    'updated_qty': True,
                    'original_qty': stock_quant.quantity + e.product_uom_qty * e.product_id.deduct_amount_parent_product
                })

        products = self.env['product.product'].search([])
        self.env['product.product'].browse(products.ids)._compute_quantities_dict(
            self._context.get('lot_id'),
            self._context.get(
                'owner_id'),
            self._context.get(
                'package_id'),
            self._context.get(
                'from_date'),
            to_date=datetime.today())
        multiple_stock_sku = {}
        for e in picking.sale_id.order_line:
            if e.product_id.product_tmpl_id.multiple_sku_one_stock:
                if e.product_id.product_tmpl_id.multiple_sku_one_stock:
                    if e.product_id.product_tmpl_id.id in multiple_stock_sku:
                        pass
                    else:
                        multiple_stock_sku[e.product_id.product_tmpl_id.id] = e.product_id.product_tmpl_id
            else:
                magento_backend = self.env['magento.backend'].search([])
                stock_quant = self.env['stock.quant'].search(
                    [('product_id', '=', e.product_id.id), ('location_id', '=', self.location_id.id)])
                if e.product_id.is_magento_product and self.location_id.is_from_magento:
                    try:
                        params = {
                            "sourceItems": [
                                {
                                    "sku": e.product_id.default_code,
                                    "source_code": self.location_id.magento_source_code,
                                    "quantity": stock_quant.quantity,
                                    "status": 1
                                }
                            ]
                        }
                        client = Client(magento_backend.web_url, magento_backend.access_token, True)
                        client.post('rest/V1/inventory/source-items', arguments=params)
                    except Exception as a:
                        raise UserError(('Can not update quantity product on source magento - %s') % tools.ustr(a))
        if len(multiple_stock_sku) > 0:
            for e in multiple_stock_sku:
                stock_quant = self.env['stock.quant'].search(
                    [('product_id', '=', multiple_stock_sku[e].variant_manage_stock.id),
                     ('location_id', '=', self.location_id.id)])
                magento_backend = self.env['magento.backend'].search([])
                for f in multiple_stock_sku[e].product_variant_ids:
                    if f.is_magento_product and self.location_id.is_from_magento:
                        try:
                            params = {
                                "sourceItems": [
                                    {
                                        "sku": f.default_code,
                                        "source_code": self.location_id.magento_source_code,
                                        "quantity": stock_quant.quantity * multiple_stock_sku[e].variant_manage_stock.deduct_amount_parent_product / f.deduct_amount_parent_product,
                                        "status": 1
                                    }
                                ]
                            }
                            client = Client(magento_backend.web_url, magento_backend.access_token, True)
                            print(123)
                            client.post('rest/V1/inventory/source-items', arguments=params)

                        except Exception as a:
                            raise UserError(
                                ('Can not update quantity product on source magento - %s') % tools.ustr(a))
        return action


class StockMove(models.Model):
    _inherit = "stock.move"

    to_refund = fields.Boolean(string="To Refund (update SO/PO)", copy=False,
                               help='Trigger a decrease of the delivered/received quantity in the associated Sale Order/Purchase Order',
                               default=True)


class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    def _get_scrap_uom(self):
        unit_measure = self.env.ref('uom.product_uom_unit').id
        return unit_measure

    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        required=True, states={'done': [('readonly', True)]}, domain=lambda self: self._get_domain_product_uom_id(),
        default=lambda self: self._get_scrap_uom())
    date_scrap = fields.Date()

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            pass

    @api.onchange('product_id')
    def _get_domain_product_uom_id(self):
        unit_measure = self.env.ref('uom.product_uom_unit').id
        # product_uom = self.product_id.uom_id.id
        return {'domain': {'product_uom_id': [('id', 'in', [unit_measure])]}}

    def action_validate(self):
        self.date_scrap = date.today()
        super(StockScrap, self).action_validate()
