# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Carlos Silveira.
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

{
    'name': 'Importa NFe - xml',
    'version': '1',
    'depends': [
        'l10n_br_base',
    ],
    'author': 'ATS Solucoes',
    'description': '''Import NFe files''',
    'website': 'http://www.atsti.com.br',
    'category': 'Tool',
    'init_xml': [],
    'demo_xml': [
    ],

    'data':  [
                    'import_xml_view.xml',
                    'security/security_groups.xml',
                    'security/ir.model.access.csv',
                    ],
    'active': False,
    'installable': True,
    'images': ['images/chain_form.png','images/template_list.png'],

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
