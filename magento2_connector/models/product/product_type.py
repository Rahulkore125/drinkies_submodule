import base64
from urllib.request import Request, urlopen

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...utils.magento.product import Client


class ProductType(models.Model):
    _inherit = "product.template"

    type = fields.Selection(
        selection_add=[('magento_simple', 'Magento Simple'),
                       ('magento_virtual', 'Magento Virtual'),
                       ('magento_downloadable', 'Magento Downloadable'),
                       ('magento_configurable', 'Magento Configurable'),
                       ('magento_grouped', 'Magento Grouped'),
                       ('magento_bundle', 'Magento Bundle'),
                       ('magento_giftcard', 'Magento Giftcard')]
    )
    magento_product_type = fields.Selection(string="Magento Product Type",
                                            selection=[('consu', 'Consumable'),
                                                       ('service', 'Service'),
                                                       ('magento_simple', 'Magento Simple'),
                                                       ('magento_virtual', 'Magento Virtual'),
                                                       ('magento_downloadable', 'Magento Downloadable'),
                                                       ('magento_configurable', 'Magento Configurable'),
                                                       ('magento_grouped', 'Magento Grouped'),
                                                       ('magento_bundle', 'Magento Bundle'),
                                                       ('magento_giftcard', 'Magento Giftcard')],
                                            required=False, )
    is_magento_product = fields.Boolean("Is Magento Product")
    categories = fields.Many2many(string="Categories", comodel_name='product.category')

    @api.model
    def import_image(self):
        for rec in self:
            if rec.is_magento_product:
                backend_id = rec.product_variant_ids[0].magento_bind_ids[0].backend_id
                url = backend_id.web_url
                access_token = backend_id.access_token
                sku = rec.default_code
                client = Client(url, access_token)
                if str(sku) != '':
                    gallery = client.call('rest/V1/products/' + str(sku) + '/media', '')
                    if len(gallery) > 0:
                        file = gallery[0]['file']
                        link = url + '/media/catalog/product' + file
                        try:
                            if link:
                                req = Request(link, headers={'User-Agent': 'Mozilla/5.0'})
                                profile_image = base64.encodebytes(urlopen(req).read())
                                val = {
                                    'image_medium': profile_image,
                                }
                                rec.image_small = profile_image
                        except:
                            raise UserError(_('Please provide correct URL or check your image size.!'))
