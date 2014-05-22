# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2014  Rafael da Silva Lima - KMEE, www.kmee.com.br               #
#                                                                             #
#This program is free software: you can redistribute it and/or modify         #
#it under the terms of the GNU Affero General Public License as published by  #
#the Free Software Foundation, either version 3 of the License, or            #
#(at your option) any later version.                                          #
#                                                                             #
#This program is distributed in the hope that it will be useful,              #
#but WITHOUT ANY WARRANTY; without even the implied warranty of               #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                #
#GNU Affero General Public License for more details.                          #
#                                                                             #
#You should have received a copy of the GNU Affero General Public License     #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.        #
###############################################################################

from openerp.osv import osv, fields
from pysped.nfe import ProcessadorNFe
from pysped.nfe.processador_nfe import ProcessadorNFe

class NfeCarta(osv.osv_memory):
    _name='nfe.carta'
    
    _columns = {
        'mensagem': fields.char('Mensagem', size=1000),
                }
    
    def _check_name(self, cr, uid, ids):
        
        for nfe in self.browse(cr, uid, ids):

            if not (len(nfe.mensagem) >= 15):
                return False
        
        return True
    
    _constraints = [(_check_name, 'Tamanho de mensagem inválida !', ['mensagem'])]
    
    def action_enviar_carta(self, cr, uid, ids, context=None):

        if context is None:
            context = {}
    
        p = ProcessadorNFe()
        
        msg = self.browse(cr, uid, ids)[0].mensagem
        
        invoice = self.pool.get('account.invoice')
        invoice_ids = context and context.get('active_ids') or []
        
        obj_invoice = self.pool.get('account.invoice')
        
        if invoice_ids:
            nfe_key = obj_invoice.browse(cr, uid, invoice_ids[0]).nfe_access_key
            
            # Ambiente 1 = Produção e 2 = Homologação
            p.corrigir_nota_evento(ambiente=2, chave_nfe= nfe_key, numero_sequencia=1, correcao= msg)
        
            
        return {'type': 'ir.actions.act_window_close'}
    
        
#  A mensagem deverá ser enviada no seguinte atributo: xCorrecao minimo 15 maximo 1000
#  No pysped o método corrigir_nota_evento deverá ser utilizado processador_nfe.py 

NfeCarta()
        
        
        
        
        
        
        