# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2014  KMEE - www.kmee.com.br - Luis Felipe Miléo              #
#                                                                             #
#This program is free software: you can redistribute it and/or modify         #
#it under the terms of the GNU Affero General Public License as published by  #
#the Free Software Foundation, either version 3 of the License, or            #
#(at your option) any later version.                                          #
#                                                                             #
#This program is distributed in the hope that it will be useful,              #
#but WITHOUT ANY WARRANTY; without even the implied warranty of               #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                #
#GNU General Public License for more details.                                 #
#                                                                             #
#You should have received a copy of the GNU General Public License            #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.        #
###############################################################################

import os
import base64
import commands
from openerp.osv import osv,orm, fields
from openerp.tools.translate import _
from openerp.addons.nfe.sped.nfe.processing.xml import monta_caminho_nfe, monta_caminho_inutilizacao


class AccountInvoiceInvalidNumber(orm.Model):
    _inherit = 'l10n_br_account.invoice.invalid.number'

    def attach_file_event(self, cr, uid, ids, seq, att_type, ext, context):

        if seq == None:
            seq = 1
        # monta_caminho_inutilizacao
        for obj in self.browse(cr, uid, ids):
            company_pool = self.pool.get('res.company')
            company = company_pool.browse(cr, uid, obj.company_id.id)
            number_start = obj.number_start
            number_end = obj.number_end
            number_serie = self.browse(cr, uid, ids, context)[0].document_serie_id.code

            if att_type == 'inu':
                save_dir = monta_caminho_inutilizacao(company, None, number_serie, number_start, number_end)
                comando = 'ls ' + save_dir + '*-inu.xml| grep -E "[0-9]{41}-inu.xml"'
                if os.system(comando) == 0:
                    arquivo = commands.getoutput(comando)
                key = arquivo[-49:-8]
                str_aux = arquivo[-49:]

            obj_attachment = self.pool.get('ir.attachment')

            try:
                file_attc=open(arquivo,'r')
                attc = file_attc.read()

                attachment_id = obj_attachment.create(cr, uid, {
                    'name': str_aux.format(key),
                    'datas': base64.b64encode(attc),
                    'datas_fname': str_aux.format(key),
                    'description': '' or _('No Description'),
                    'res_model': 'l10n_br_account.invoice.invalid.number',
                    'res_id': obj.id
                    }, context=context)
            except IOError:
                key = 'erro'
            else:
                file_attc.close()

        return True


class AccountInvoice(orm.Model):
    _inherit = 'account.invoice'

    def attach_file_event(self, cr, uid, ids, seq, att_type, ext, context):

        if seq == None:
            seq = 1

        for inv in self.browse(cr, uid, ids):
            company_pool = self.pool.get('res.company')
            company = company_pool.browse(cr, uid, inv.company_id.id)
            nfe_key = inv.nfe_access_key

            if att_type != 'nfe' and att_type != None:
                str_aux = nfe_key + '-%02d-%s.%s' % (seq, att_type, ext)
                save_dir = os.path.join(monta_caminho_nfe(company, chave_nfe=nfe_key) + str_aux)

            elif att_type == None and ext == 'pdf':
                str_aux = nfe_key + '.%s' % (ext)
                save_dir = os.path.join(monta_caminho_nfe(company, chave_nfe=nfe_key) + str_aux)

            elif att_type == 'nfe' and ext == 'xml':
                str_aux = nfe_key + '-%s.%s' % (att_type, ext)
                save_dir = os.path.join(monta_caminho_nfe(company, chave_nfe=nfe_key) + str_aux)

            obj_attachment = self.pool.get('ir.attachment')

            try:
                file_attc=open(save_dir,'r')
                attc = file_attc.read()

                attachment_id = obj_attachment.create(cr, uid, {
                    'name': str_aux.format(nfe_key),
                    'datas': base64.b64encode(attc),
                    'datas_fname': str_aux.format(nfe_key),
                    'description': '' or _('No Description'),
                    'res_model': 'account.invoice',
                    'res_id': inv.id
                    }, context=context)
            except IOError:
                key = 'erro'
            else:
                file_attc.close()

        return True


    def action_invoice_sent(self, cr, uid, ids, context=None):
        
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        attach_obj = self.pool.get('ir.attachment')
        attachment_ids = attach_obj.search(cr, uid, [('res_model', '=', 'account.invoice'), ('res_id', '=', ids[0])], context=context)
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'nfe_attach', 'email_template_nfe')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(context)
        ctx.update({
            'default_model': 'account.invoice',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_invoice_as_sent': True,
            'attachment_ids': [(6, 0, attachment_ids)] ,
            })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    
class email_template(osv.Model):
    _inherit = 'email.template'
 
    def generate_email(self, cr, uid, template_id, res_id, context=None):
        context = context or {}
        values =  super(email_template, self).generate_email( cr, uid, template_id, res_id, context)
        if context.get('default_model') == 'account.invoice':
            values['attachment_ids'] = context.get('attachment_ids')
        return values
        
        
class res_company(osv.Model):
    _inherit = 'res.company'

    _columns = {
    'nfe_email': fields.text('Observação em Email NFe'),
            }
