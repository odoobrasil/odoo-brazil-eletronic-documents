# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).


{
    'name': 'NFS-e São Paulo',
    'summary': """Módulo que implementa o Layout da cidade de São Paulo
                Depends: PyTrustnfe""",
    'version': '8.0',
    'category': 'Localisation',
    'author': 'Trustcode',
    'license': 'AGPL-3',
    'website': 'http://www.trustcode.com.br',
    'contributors': [
        'Danimar Ribeiro <danimaribeiro@gmail.com>',
        'Carlos Silveira <crsilveira@gmail.com>',
    ],
    'depends': [
        'base_nfse'
    ],
    'data': [
        'report/danfse.xml',
        'views/account_invoice_view.xml',
        'views/res_partner.xml',
        'wizard/consulta_nfse.xml',
    ],
    'instalable': True
}
