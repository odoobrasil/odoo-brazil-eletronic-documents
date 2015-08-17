# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2014 Rodolfo Leme Bertozo - KMEE - www.kmee.com.br            #
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

from openerp.osv import orm, fields
import os
import commands
import base64


class NfeXmlPeriodicExport(orm.TransientModel):

    _name = 'nfe.xml.periodic.export'
    _description = 'Export NFes'
    _columns = {
        'name': fields.char('Nome', size=255),
        'start_period_id': fields.many2one('account.period',
                                           u'Período Inicial'),
        'stop_period_id': fields.many2one('account.period',
                                          u'Período Final'),
        'zip_file': fields.binary('Zip Files', readonly=True),
        'state': fields.selection([('init', 'init'),
                                   ('done', 'done')], 'state', readonly=True),
    }

    _defaults = {
        'state': 'init',
    }

    def done(self, cr, uid, ids, context=False):
        return True

    def export(self, cr, uid, ids, context=False):
        a = self.pool.get('res.company')
        result = 0
        # Define a empresa correta se for multcompany
        company_id = a._company_default_get(cr, uid)
        obj_res_company = a.browse(cr, uid, company_id)
        export_dir = str(obj_res_company.nfe_export_folder)

        if export_dir == 'False':
            raise orm.except_orm(
                u'Erro!',
                u'Necessário configurar pasta de exportação da empresa.',)

        caminho = export_dir

        # completa o caminho com homologacao ou producao
        if obj_res_company.nfe_environment == '1':
            caminho = os.path.join(caminho, 'producao')
        elif obj_res_company.nfe_environment == '2':
            caminho = os.path.join(caminho, 'homologacao')

        try:
            # Diretorios de importacao, diretorios com formato do ano e mes
            dirs_date = os.listdir(caminho)
        except:
            raise orm.except_orm(
                u'Erro!',
                u'Necessário configurar pasta de exportação da empresa.',)

        for obj in self.browse(cr, uid, ids):
            data = False
            caminho_arquivos = ''
            date_start = obj.start_period_id.date_start
            date_stop = obj.stop_period_id.date_stop

            if date_start[:7] == date_stop[:7]:
                bkp_name = 'bkp_' + date_start[:7] + '.zip'
            else:
                bkp_name = 'bkp_' + \
                    date_start[:7] + '_' + date_stop[:7] + '.zip'

            for diretorio in dirs_date:
                # se houver arquivos fora do padrão (ano-mes, aaaa-mm) dentro
                #  da pasta de exportação
                try:
                    if (int(diretorio[:4]) >= int(date_start[:4]) and
                            int(diretorio[5:]) >= int(date_start[5:7])) and \
                            (int(diretorio[:4]) <= int(date_stop[:4]) and
                                int(diretorio[5:]) <= int(date_stop[5:7])):

                        caminho_aux = os.path.join(caminho, diretorio)
                        dirs_nfes = os.listdir(caminho_aux)

                        for diretorio_final in dirs_nfes:

                            caminho_final = os.path.join(caminho_aux,
                                                         diretorio_final) + '/'
                            comando_cce = 'ls ' + caminho_final + \
                                          '*-??-cce.xml'
                            comando_can = 'ls ' + caminho_final + \
                                          '*-??-can.xml'
                            comando_nfe = 'ls ' + caminho_final + \
                                          '*-nfe.xml| grep -E ' \
                                          '"[0-9]{44}-nfe.xml"'
                            comando_inv = 'ls ' + caminho_final + \
                                          '*-inu.xml| grep -E ' \
                                          '"[0-9]{41}-inu.xml"'

                            if os.system(comando_cce) == 0:
                                str_aux = commands.getoutput(comando_cce)
                                caminho_arquivos = caminho_arquivos + \
                                    str_aux + ' '

                            if os.system(comando_can) == 0:
                                str_aux = commands.getoutput(comando_can)
                                caminho_arquivos = caminho_arquivos + \
                                    str_aux + ' '

                            if os.system(comando_inv) == 0:
                                str_aux = commands.getoutput(comando_inv)
                                caminho_arquivos = caminho_arquivos + \
                                    str_aux + ' '

                            str_aux = commands.getoutput(comando_nfe)
                            if os.system(comando_nfe) == 0:
                                str_aux = commands.getoutput(comando_nfe)
                                caminho_arquivos = caminho_arquivos + \
                                    str_aux + ' '

                        # troca \n por espaços
                        caminho_arquivos = caminho_arquivos.replace('\n', ' ')
                        result = os.system("zip -r " + os.path.join(export_dir,
                                                                    bkp_name) +
                                           ' ' + caminho_arquivos)
                        if result:
                            raise orm.except_orm(
                                u'Erro!',
                                u'Não foi possível compactar os arquivos.',)

                        data = self.read(cr, uid, ids, [], context=context)[0]
                        orderFile = open(os.path.join(export_dir,
                                                      bkp_name), 'r')
                        itemFile = orderFile.read()

                        self.write(cr, uid, ids,
                                   {'state': 'done',
                                    'zip_file': base64.b64encode(itemFile),
                                    'name': bkp_name}, context=context)
                except:
                    pass

        if data:
            return {'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': data['id'],
                    'target': 'new', }
        else:
            raise orm.except_orm(
                u'Atenção!',
                u'Não existem arquivos nesse período'
                u' ou período inválido.',)

        return False
