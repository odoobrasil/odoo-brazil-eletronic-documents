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
from nfe.sped.nfe.processing.xml import send_correction_letter

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
            
        correcao = self.browse(cr, uid, ids)[0].mensagem
         
        obj_invoice = self.pool.get('account.invoice')
        invoice_ids = context and context.get('active_ids') or []
        invoice = obj_invoice.browse(cr, uid, invoice_ids[0])
        
         
        if invoice_ids:
            chave_nfe = invoice.nfe_access_key
             
        company_pool = self.pool.get('res.company')
        company = company_pool.browse(cr, uid, invoice.company_id.id)
        
        event_obj = self.pool.get('l10n_br_account.document_event')

        
        results = []   
        try:                
            processo = send_correction_letter(company, chave_nfe, correcao) 
            vals = {
                        'type': str(processo.webservice),
                        'status': processo.resposta.retEvento[0].infEvento.cStat.valor,
                        'response': '',
                        'company_id': company.id,
                        'origin': '[CC-E] ' + str(invoice.internal_number),
                        #'file_sent': processo.arquivos[0]['arquivo'],
                        #'file_returned': processo.arquivos[1]['arquivo'],
                        'message': processo.resposta.retEvento[0].infEvento.xMotivo.valor,
                        'state': 'done',
                        'document_event_ids': invoice.id}
            results.append(vals)
                        
        except Exception as e:
            vals = {
                    'type': '-1',
                    'status': '000',
                    'response': 'response',
                    'company_id': company.id,
                    'origin': '[CC-E]' + str(invoice.internal_number),
                    'file_sent': 'False',
                    'file_returned': 'False',
                    'message': 'Erro desconhecido ' + e.message,
                    'state': 'done',
                    'document_event_ids': invoice.id
                    }
            results.append(vals)
        finally:
            for result in results:
                event_obj.create(cr, uid, result)                
       
            
        return {'type': 'ir.actions.act_window_close'}
    
NfeCarta()
        
        
        
        
        
        
        