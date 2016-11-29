# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2014  KMEE - www.kmee.com.br - Luis Felipe Miléo              #
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

{
    'name': 'NFE XML',
    'version': '8.0.1.0.0',
    'category': 'Generic Modules',
    'description': """Salva o danfe e xml em anexo a fatura e permite o
        envio dos documentos anexados para o email do cliente""",
    'author': 'KMEE',
    'license': 'AGPL-3',
    'website': 'http://www.kmee.com.br',
    'depends': [
        'document',
        'nfe',
    ],
    'data': [
        'data/nfe_attach_email.xml',
        'wizard/nfe_xml_periodic_export.xml',
    ],
    'demo': [],
    'test': [],
    'installable': False,
    'active': False,
}
