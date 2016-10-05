# -*- coding: utf-8 -*-
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

from openerp import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    default_operation = fields.Selection(
        [('A', u"Sem Dedução"),
         ('B', u"Com dedução/Materiais"),
         ('C', u"Imune/Isenta de ISSQN"),
         ('D', u"Devolução/Simples Remessa"),
         ('J', u"Intermediação")], u"Operação")

    default_taxation = fields.Selection(
        [('C', u"Isenta de ISS"),
         ('E', u"Não incidência no município"),
         ('F', u"Imune"),
         ('K', u"Exigibilidade Susp.Dec.J/Proc.A"),
         ('N', u"Não Tributável"),
         ('T', u"Tributável"),
         ('G', u"Tributável Fixo"),
         ('H', u"Tributável S.N."),
         ('M', u"Micro Empreendedor Individual(MEI)")],
        u"Tributação")
