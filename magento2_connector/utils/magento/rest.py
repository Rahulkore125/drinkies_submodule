# coding: utf-8
try:
    import requests
    import json
except ImportError:
    pass


class Client(object):

    def __init__(self, url, token, verify_ssl=True):
        self._url = url
        self._token = token
        self._verify_ssl = verify_ssl

    def call(self, resource_path, arguments):
        url = '%s/%s' % (self._url, resource_path)
        res = requests.get(
            url, params=arguments, verify=self._verify_ssl,
            headers={'Authorization': 'Bearer %s' % self._token,
                     'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36'},
            timeout=1000)
        res.raise_for_status()
        return res.json()

    def post(self, resource_path, arguments):
        url = '%s/%s' % (self._url, resource_path)
        res = requests.post(
            url, json=arguments, verify=self._verify_ssl,
            headers={'Authorization': 'Bearer %s' % self._token,
                     'Content-Type': 'application/json'})
        # res.raise_for_status()
        return res.json()

    def adapter_magento_id(self, table, backend_id, external_id, context=None):
        context.env.cr.execute("SELECT id FROM %s WHERE backend_id=%s AND external_id=%s LIMIT 1" % (
            table.strip("'"), backend_id, external_id))
        magento_ids = context.env.cr.fetchall()[0]
        return magento_ids[0] if magento_ids else -1
