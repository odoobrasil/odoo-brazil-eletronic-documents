# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 TrustCode - www.trustcode.com.br                         #
#              Danimar Ribeiro <danimaribeiro@gmail.com>                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################

import cPickle
from openerp import api, fields, models
from openerp.tools.translate import _
from openerp.exceptions import Warning


class NfeImportEdit(models.TransientModel):
    _name = 'nfe.import.edit'

    @api.multi
    def name_get(self):
        return [(rec.id,
                 u"Editando NF-e ({0})".format(
                     rec.number)) for rec in self]

    xml_data = fields.Char(string="Xml Data", size=20000, readonly=True)
    edoc_input = fields.Binary(u'Arquivo do documento eletrônico',
                               help=u'Somente arquivos no formato TXT e XML')
    file_name = fields.Char('File Name', size=128)

    number = fields.Char(string="Número", size=20, readonly=True)
    supplier_id = fields.Many2one('res.partner', string="Fornecedor",
                                  readonly=True)

    natureza_operacao = fields.Char(string="Natureza da operação", size=200,
                                    readonly=True)
    amount_total = fields.Float(string="Valor Total", digits=(18, 2),
                                readonly=True)

    fiscal_category_id = fields.Many2one(
        'l10n_br_account.fiscal.category', 'Categoria Fiscal')
    fiscal_position = fields.Many2one(
        'account.fiscal.position', 'Posição Fiscal',
        domain="[('fiscal_category_id','=',fiscal_category_id)]")

    product_import_ids = fields.One2many('nfe.import.products',
                                         'nfe_import_id', string="Produtos")

    @api.model
    def create(self, values):
        return super(NfeImportEdit, self).create(values)

    def _validate(self):
        indice = 1
        for item in self.product_import_ids:
            print item.product_xml
            if not item.product_id:
                raise Warning(u'Escolha o produto do item {0} - {1}'.format(
                              str(indice), item.product_xml))
            if not item.cfop_id:
                raise Warning(u'Escolha a CFOP do item {0} - {1}'.format(
                              str(indice), item.product_xml))

            if not item.uom_id:
                raise Warning(u'Escolha a Unidade do item {0} - {1}'.format(
                              str(indice), item.product_xml))

            if item.product_id.uom_po_id.category_id.id !=\
                    item.uom_id.category_id.id:

                raise Warning(u'Unidades de medida incompatíveis no item \
                            {0} - {1}'.format(str(indice), item.product_xml))
            indice += 1

    @api.multi
    def confirm_values(self):
        self.ensure_one()
        self._validate()
        inv_values = cPickle.loads(self.xml_data.encode('ascii', 'ignore'))

        index = 0
        for item in self.product_import_ids:
            if not inv_values['invoice_line'][index][2]['product_id']:
                # Creating the product code related to supplier
                self.env['product.supplierinfo'].create(
                    {'name': self.supplier_id.id,
                     'product_name': item.product_xml,
                     'product_code': item.code_product_xml,
                     'product_tmpl_id': item.product_id.product_tmpl_id.id})

            inv_values['invoice_line'][index][2][
                'product_id'] = item.product_id.id
            inv_values['invoice_line'][index][2]['uos_id'] = item.uom_id.id
            inv_values['invoice_line'][index][2]['cfop_id'] = item.cfop_id.id
            index += 1

        invoice = self.env['account.invoice'].create(inv_values)
        self.attach_doc_to_invoice(invoice.id, self.edoc_input,
                                   self.file_name)

        model_obj = self.pool.get('ir.model.data')
        action_obj = self.pool.get('ir.actions.act_window')
        action_id = model_obj.get_object_reference(
            self._cr, self._uid, 'account', 'action_invoice_tree2')[1]
        res = action_obj.read(self._cr, self._uid, action_id)
        res['domain'] = res['domain'][:-1] + \
            ",('id', 'in', %s)]" % [invoice.id]
        return res

    @api.onchange('fiscal_position')
    def position_fiscal_onchange(self):
        for item in self.product_import_ids:
            item.cfop_id = self.fiscal_position.cfop_id.id

    def attach_doc_to_invoice(self, invoice_id, doc, file_name):
        obj_attachment = self.env['ir.attachment']

        attachment_id = obj_attachment.create({
            'name': file_name,
            'datas': doc,
            'description': _('Xml de entrada NF-e'),
            'res_model': 'account.invoice',
            'res_id': invoice_id
        })
        return attachment_id


class NfeImportProducts(models.TransientModel):
    _name = 'nfe.import.products'

    nfe_import_id = fields.Many2one('nfe.import.edit', string="Nfe Import")

    product_id = fields.Many2one('product.product', string="Produto")
    uom_id = fields.Many2one('product.uom', string="Unidade de Medida")
    cfop_id = fields.Many2one('l10n_br_account_product.cfop', string="CFOP")

    code_product_xml = fields.Char(
        string="Código Forn.", size=20, readonly=True)
    product_xml = fields.Char(string="Produto Forn.", size=120, readonly=True)
    uom_xml = fields.Char(string="Un. Medida Forn.", size=10, readonly=True)
    cfop_xml = fields.Char(string="CFOP Forn.", size=10, readonly=True)

    quantity_xml = fields.Float(
        string="Quantidade", digits=(18, 4), readonly=True)
    unit_amount_xml = fields.Float(
        string="Valor Unitário", digits=(18, 4), readonly=True)
    discount_total_xml = fields.Float(
        string="Desconto total", digits=(18, 2), readonly=True)
    total_amount_xml = fields.Float(
        string="Valor Total", digits=(18, 2), readonly=True)

    @api.onchange('product_id')
    def product_onchange(self):
        if self.product_id.uom_po_id and self.uom_id:
            if self.product_id.uom_po_id.category_id.id != self.uom_id.category_id.id:
                return {'value': {},
                        'warning': {'title': 'Atenção',
                                    'message': u'Unidades de medida incompatíveis'}}
        self.uom_id = self.product_id.uom_po_id.id

    @api.onchange('uom_id')
    def uom_onchange(self):
        if self.product_id.uom_po_id and self.uom_id:
            if self.product_id.uom_po_id.category_id.id != self.uom_id.category_id.id:
                return {'value': {},
                        'warning': {'title': 'Atenção',
                                    'message': u'Unidades de medida incompatíveis'}}
