# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2016 TrustCode - www.trustcode.com.br                         #
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


from openerp import api, fields, models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    icms_credit = fields.Boolean("Creditar ICMS?")
    ipi_credit = fields.Boolean("Creditar IPI?")
    pis_credit = fields.Boolean("Creditar PIS?")
    cofins_credit = fields.Boolean("Creditar COFINS?")

    def _apply_mapping(self, tax_mapping, inv_line):
        if tax_mapping.tax_code_dest_id:
            inv_line[
                'icms_cst_id'] = tax_mapping.tax_code_dest_id.id
        if tax_mapping.cfop_dest_id:
            inv_line['cfop_id'] = tax_mapping.cfop_dest_id.id
        if tax_mapping.tax_dest_id:
            line_tax = []
            for tax_line in inv_line['invoice_line_tax_id']:
                tax = self.env['account.tax'].browse(tax_line[1])
                if tax.domain != tax_mapping.tax_dest_id.domain:
                    line_tax.append(tax_line)
                else:
                    line_tax.append((4, tax_mapping.tax_dest_id.id, 0))

            inv_line['invoice_line_tax_id'] = line_tax

    @api.multi
    def fiscal_position_map(self, inv_line):
        values = dict(inv_line or {})
        self.ensure_one()
        values['cfop_id'] = self.cfop_id.id
        for tax_mapping in self.tax_ids:
            if tax_mapping.cfop_src_id  and tax_mapping.tax_src_id  and\
                    tax_mapping.tax_code_src_id:

                if tax_mapping.tax_code_src_id.id == values['icms_cst_id'] and \
                        tax_mapping.cfop_src_id.code == str(values['cfop_xml']) and \
                        tax_mapping.tax_src_id.id in [j[1] for j in values['invoice_line_tax_id']]:

                    self._apply_mapping(tax_mapping, values)
                    continue

            if tax_mapping.cfop_src_id and tax_mapping.tax_src_id:

                if tax_mapping.cfop_src_id.code == str(values['cfop_xml']) and \
                        tax_mapping.tax_src_id.id in [j[1] for j in values['invoice_line_tax_id']]:

                    self._apply_mapping(tax_mapping, values)
                    continue

            if tax_mapping.cfop_src_id and tax_mapping.tax_code_src_id:

                if tax_mapping.cfop_src_id.code == str(values['cfop_xml']) and \
                        tax_mapping.tax_code_src_id.id == values['icms_cst_id']:

                    self._apply_mapping(tax_mapping, values)
                    continue

            if tax_mapping.tax_src_id and tax_mapping.tax_code_src_id:

                if tax_mapping.tax_code_src_id.id == values['icms_cst_id'] and \
                        tax_mapping.tax_src_id.id in [j[1] for j in values['invoice_line_tax_id']]:

                    self._apply_mapping(tax_mapping, values)
                    continue

            if tax_mapping.tax_code_src_id:
                if tax_mapping.tax_code_src_id.id == values['icms_cst_id']:
                    # A CST de Origem bate então tenta setar CFOP e CST de
                    # destino se existir
                    self._apply_mapping(tax_mapping, values)
                    continue

            if tax_mapping.cfop_src_id:
                if tax_mapping.cfop_src_id.id == values['cfop_xml']:
                    # A CFOP de origem bate então tenta setar CFOP e CST de
                    # destino se existir
                    self._apply_mapping(tax_mapping, values)

        return (0, 0, values)


class AccountFiscalPositionTax(models.Model):
    _inherit = 'account.fiscal.position.tax'

    type = fields.Selection(related='position_id.type', string="Tipo")

    cfop_src_id = fields.Many2one(
        'l10n_br_account_product.cfop',
        string=u"CFOP de Origem",
        help=u"Apenas válido para a importação do xml")
    cfop_dest_id = fields.Many2one(
        'l10n_br_account_product.cfop',
        string=u"CFOP de Destino",
        help=u"Apenas válido para a importação do xml")
