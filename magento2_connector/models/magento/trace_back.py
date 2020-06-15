from odoo import api, fields, models


class TraceBack(models.Model):
    _name = "trace.back.information"
    _order = "time_log desc"

    time_log = fields.Datetime(string="Time")
    infor = fields.Text(string="Information")
