# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 TrustCode - www.trustcode.com.br                         #
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


class NfeImportCfopMapping(models.Model):
    _name = 'nfe.import.cfop.mapping'
    
    cfop_origin_id = fields.Many2one('l10n_br_account_product.cfop', 
                                     u'CFOP de Origem')
    
    cfop_dest_id = fields.Many2one('l10n_br_account_product.cfop', 
                                     u'CFOP de Destino')
    
    
class NfeImportCSTMapping(models.Model):    
    _name = 'nfe.import.cst.mapping'
    
    
    cst_origin_id = fields.Many2one('account.tax.code',
                                    u'CST de Origem')
    
    cst_dest_id = fields.Many2one('account.tax.code',
                                    u'CST de Destino')
    
    