from ..magento.rest import Client


class Location(Client):
    __slots__ = ()

    def list_all_sources(self):
        return self.call('rest/V1/inventory/sources', 'searchCriteria')

    def insert_source(self, sources, backend_id, url, token, context=None):
        for source in sources:
            odoo_location = context.env['stock.location'].search(
                [('is_from_magento', '=', True), ('magento_source_code', '=', source['source_code'])])
            warehouse_location = context.env['stock.warehouse'].search([('active', '=', True)]).view_location_id

            if len(odoo_location) > 0:
                odoo_location.write({
                    'name': source['name'],
                    'is_from_magento': True,
                    'magento_source_code': source['source_code'],
                    'type': 'internal',
                    'postcode': source['postcode'],
                    'active': source['enabled'],
                    'location_id': warehouse_location.id
                })
            else:
                odoo_location = context.env['stock.location'].create({
                    'name': source['name'],
                    'is_from_magento': True,
                    'magento_source_code': source['source_code'],
                    'type': 'internal',
                    'postcode': source['postcode'],
                    'active': source['enabled'],
                    'location_id': warehouse_location.id
                })

                context.env['magento.source'].create({
                    'odoo_id': odoo_location.id,
                    'backend_id': backend_id
                })
