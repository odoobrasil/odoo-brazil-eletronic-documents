# -*- encoding: utf-8 -*-
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
#                                                                             #
###############################################################################

{
    'name': 'Importação de XML Diretamente do Manifesto',
    'version': '1.0',
    'category': 'NFE',
    'description': """Integra os módulos de importação do xml e
        manifesto de destinatário""",
    'author': 'Danimar Ribeiro - Trustcode',
    'license': 'AGPL-3',
    'website': 'http://www.trustcode.com.br',
    'contributors': ['Danimar Ribeiro <danimaribeiro@gmail.com>',
                     'Mackilem Van der Laan Soares <mack.vdl@gmail.com>'
                     ],
    'description': """
        Com este módulo você pode programar para realizar a importação automática
        de NF-e apartir do módulo de Manifesto do Destinatário (MDE).
        O MDE periodicamente busca as notas destinadas a empresa, este módulo
        pega as notas baixadas e faz a importação.
    """,
    'depends': [
        'nfe_import',
        'nfe_mde',
    ],
    'data': [
        'views/nfe_mde_view.xml',
        'report/report_danfe.xml',
        'wizard/wizard_nfe_import_xml_view.xml',
    ],
    'installable': True
}
