from odoo import models


class CRMRoutines(models.Model):
    _name = 'crm.routines'

    def init(self):
        self.env.cr.execute("""
        CREATE OR REPLACE FUNCTION combine_id(p_backend_id integer, p_amount double precision, p_default_code character varying,
                                      p_product_id integer)
  RETURNS TABLE
          (
            account_tax             integer,
            product_product         integer,
            magento_product_product integer
          ) AS
$BODY$
DECLARE
  account_tax_id int;
BEGIN
  account_tax_id =
      (SELECT id AS account_tax FROM account_tax WHERE backend_id = p_backend_id AND amount = p_amount LIMIT 1);

  RETURN QUERY
    SELECT *
    FROM (
            (SELECT account_tax_id AS account_tax) t1
           LEFT JOIN
         (SELECT id AS product_product FROM product_product WHERE default_code like p_default_code LIMIT 1) t2
         ON t1.account_tax >= 0
           LEFT JOIN
         (SELECT odoo_id AS magento_product_product
          FROM magento_product_product
          WHERE backend_id = p_backend_id
            AND external_id = p_product_id
          LIMIT 1) t3
         ON t3.magento_product_product >= 0
           );

END
$BODY$
  LANGUAGE plpgsql;
        """)
