# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (C) 2014  Luis Felipe Mileo - KMEE, www.kmee.com.br
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
###############################################################################

from openerp.addons.nfe.sped.nfe.processing.xml import check_partner
from openerp.addons.nfe.sped.nfe.validator.config_check import \
    validate_nfe_configuration
import xml.etree.ElementTree as ET
from openerp.osv import orm
from openerp.tools.translate import _
from openerp import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    habilitado_sintegra = fields.Boolean('Habilitado no Sintegra',
                                         readonly=True)

    @api.multi
    def sefaz_check(self):

        validate_nfe_configuration(self.company_id)

        for partner in self:
            if partner.cnpj_cpf:
                cnpj_cpf = partner.cnpj_cpf

                estato = partner.state_id.code or None
                ie = partner.inscr_est or None
                ie = ie if ie != 'ISENTO' else None

                processo = check_partner(self.company_id, cnpj_cpf, estato, ie)
                xml = processo.resposta.xml.encode('utf-8')

                tree = ET.fromstring(xml)
                info = {}

                for child in tree:
                    info[child.tag[36:]] = child.text
                    for infCons in child:
                        info[infCons.tag[36:]] = infCons.text
                        for infCad in infCons:
                            info[infCad.tag[36:]] = infCad.text
                            for end in infCad:
                                info[end.tag[36:]] = end.text

                if info['cStat'] not in ('111', '112'):
                    raise orm.except_orm(
                        _("Erro ao se comunicar com o SEFAZ"),
                        _("%s - %s") % (info.get('cStat', ''),
                                        info.get('xMotivo', '')))

                city_id = None
                if "cMun" in info:
                    city_id = self.env['l10n_br_base.city'].search(
                        [('ibge_code', '=', info['cMun'][2:])])[0]
                if "xMun" in info and not city_id:
                    city_id = self.env['l10n_br_base.city'].search(
                        [('name', 'ilike', info['xMun']),
                         ('state_id', '=', partner.state_id.id)])

                result = {
                    'district': info.get('xBairro', ''),
                    'street': info.get('xLgr', ''),
                    'zip': info.get('CEP', ''),
                    'street2': info.get('xCpl', ''),
                    'legal_name': info.get('xNome', ''),
                    'number': info.get('nro', ''),
                    'l10n_br_city_id': city_id and city_id.id or None,
                    'habilitado_sintegra': info['cSit'],
                    'inscr_est': info.get('IE', False) or ie,
                }
                partner.write(result)
        return
