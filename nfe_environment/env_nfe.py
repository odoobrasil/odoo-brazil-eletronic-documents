# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Luis Felipe Miléo
#    Copyright 2015 KMEE INFORMATICA LTDA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from openerp.osv import orm, fields

from openerp.addons.server_environment import serv_config


class ResCompany(orm.Model):

    _inherit = 'res.company'

    def _get_nfe_conf(self, cr, uid, ids, name, args, context=None):
        """
        Return configuration
        """
        res = {}
        for company in self.browse(cr, uid, ids, context=context):
            global_section_name = 'nfe'

            # default vals
            config_vals = {'nfe_environment': '2'}
            if serv_config.has_section(global_section_name):
                config_vals.update((serv_config.items(global_section_name)))

            custom_section_name = '.'.join((global_section_name,
                                            company.name))
            if serv_config.has_section(custom_section_name):
                config_vals.update(serv_config.items(custom_section_name))

            if config_vals.get('nfe_environment'):
                config_vals['nfe_environment'] = config_vals['nfe_environment']

            res[company.id] = config_vals
        return res

    _columns = {
        'nfe_environment': fields.function(
            _get_nfe_conf,
            string='Ambiente Padrão',
            type="selection",
            selection=[('1', u'Produção'),
                       ('2', u'Homologação')],
            multi='income_nfe_config',
            # fnct_search=_type_search,
            states={'draft': [('readonly', True)]},
        ),
    }
