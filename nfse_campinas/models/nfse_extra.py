# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 Trustcode - www.trustcode.com.br                         #
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


import logging

from openerp import api, fields, models


_logger = logging.getLogger(__name__)


class NFSeConsultaPorData(models.Model):
    _name = 'nfse.consulta.data'

    data_inicio = fields.Date('Inicio', required=True)
    data_final = fields.Date('Final', required=True)
    nota_inicial = fields.Integer('Numeração Inicial', required=True)

    @api.multi
    def action_consultar_notas(self):
        base_nfse = self.env['base.nfse'].create(
            {'company_id': self.env.user.company_id.id,
             'city_code': '6291',
             'certificate': self.env.user.company_id.nfe_a1_file,
             'password': self.env.user.company_id.nfe_a1_password})

        base_nfse.consulta_nfse_por_data(
            self.data_inicio,
            self.data_final,
            '1', '99')
        return
