# -*- coding: utf-8 -*-
# from odoo import http


# class ChamcongTinhluong(http.Controller):
#     @http.route('/chamcong_tinhluong/chamcong_tinhluong', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/chamcong_tinhluong/chamcong_tinhluong/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('chamcong_tinhluong.listing', {
#             'root': '/chamcong_tinhluong/chamcong_tinhluong',
#             'objects': http.request.env['chamcong_tinhluong.chamcong_tinhluong'].search([]),
#         })

#     @http.route('/chamcong_tinhluong/chamcong_tinhluong/objects/<model("chamcong_tinhluong.chamcong_tinhluong"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('chamcong_tinhluong.object', {
#             'object': obj
#         })
