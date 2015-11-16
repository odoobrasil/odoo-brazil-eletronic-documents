# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2014  KMEE  - www.kmee.com.br - Rafael da Silva Lima          #
# Copyright (C) 2015  KMEE  - www.kmee.com.br - Luis Felipe Miléo             #
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
###############################################################################


from openerp import models, fields

class ResCompany(models.Model):

    _inherit = 'res.company'

    is_nfe_check_service = fields.Boolean(string=u"Consulta serviço ao enviar")
    is_nfe_save_files = fields.Boolean(string="Salvar Arquivos")
    nfe_send_method = fields.Selection(
        string="Emissão",
        selection=[
            ('normal', 'Normal'),
            ('contingencia', u'Contingência'),
            ('contingencia_scan', u'Contingência Scan'),
        ], required=True, default='normal')
    nfe_report_layout = fields.Selection(
        string="Formato Danfe",
        selection=[
            ('1', 'Retrato'),
            ('2', 'Paisagem (Não implementado)'),
        ], required=False, )
    nfe_temp_path = fields.Char(
        string="Caminho Temporario",
        required=False)
    nfe_max_receipt_check = fields.Integer(
        string=u"Nº Máximo de tentativas de consulta do Recibo",
        required=True,
        default=5)
    nfe_email = fields.Text(string='Observação em Email NFe')