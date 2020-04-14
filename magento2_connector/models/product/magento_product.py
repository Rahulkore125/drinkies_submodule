import base64
from urllib.request import Request, urlopen

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from ...utils.magento.product import Client


class MagentoProductProduct(models.Model):
    _name = 'magento.product.product'
    # current ignore this because parent products can have same child products
    # _inherit = 'magento.binding'
    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        string='Magento Backend',
        required=True,
        ondelete='restrict',
    )
    external_id = fields.Integer(string='ID on Magento')

    _inherits = {'product.product': 'odoo_id'}
    _description = 'Magento Product'

    odoo_id = fields.Many2one('product.product',
                              string='Product',
                              required=True,
                              ondelete="cascade")

    website_ids = fields.Many2many(comodel_name='magento.website',
                                   string='Websites',
                                   readonly=True)
    created_at = fields.Date('Created At (on Magento)')
    updated_at = fields.Date('Updated At (on Magento)')

    @api.model
    def import_image(self):
        for rec in self:
            backend_id = rec.backend_id
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
