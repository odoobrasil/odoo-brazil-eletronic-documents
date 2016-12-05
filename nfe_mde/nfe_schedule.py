# coding: utf-8
###############################################################################
#                                                                             #
# Copyright (C) 2015  Danimar Ribeiro www.trustcode.com.br                    #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU Affero General Public License for more details.                         #
#                                                                             #
# You should have received a copy of the GNU Affero General Public License    #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
###############################################################################

import re

from openerp import models, api, fields


class NfeSchedule(models.TransientModel):
    _name = 'nfe.schedule'

    state = fields.Selection(
        string="Estado",
        selection=[('init', 'Não iniciado'), ('done', 'Finalizado')],
        default='init'
    )

    @staticmethod
    def _mask_cnpj(cnpj):
        if cnpj:
            val = re.sub('[^0-9]', '', cnpj)
            if len(val) == 14:
                cnpj = "%s.%s.%s/%s-%s" % (val[0:2], val[2:5], val[5:8],
                                           val[8:12], val[12:14])
        return cnpj

    @api.model
    def schedule_download(self, raise_error=False, domain=()):
        companies = self.env['res.company'].search(domain)
        return companies.query_nfe_batch(raise_error=raise_error)

    @api.multi
    def execute_download(self):
        for record in self:
            record.schedule_download(raise_error=True)
