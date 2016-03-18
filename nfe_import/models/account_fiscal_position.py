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


class AccountFiscalPositionTax(models.Model):
    _inherit = 'account.fiscal.position.tax'

    cfop_src_id = fields.Many2one(
        'l10n_br_account_product.cfop',
        string=u"CFOP de Origem",
        help=u"Apenas válido para a importação do xml")
    cfop_dest_id = fields.Many2one(
        'l10n_br_account_product.cfop',
        string=u"CFOP de Destino",
        help=u"Apenas válido para a importação do xml")
