# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 TrustCode - www.trustcode.com.br                         #                                    #
#    Authors: Luis Felipe Mileo                                               #
#            Fernando Marcato Rodrigues                                       #
#            Daniel Sadamo Hirayama                                           #
#            Danimar Ribeiro <danimaribeiro@gmail.com>                        #
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

import re
import base64
import string
from datetime import datetime
import tempfile

from openerp import pooler
from openerp.osv import orm
from openerp.tools.translate import _
import pysped
from pysped.nfe.leiaute.consrecinfe_310 import ProtNFe


class NFe310(object):

    def __init__(self):
        self.nfe = None
        self.nfref = None
        self.det = None
        self.dup = None

    def deserialize(self, cr, uid, nfe, context):
        if not context:
            context = {'lang': 'pt_BR'}
        if nfe.infNFe.ide.tpNF.valor == 0:
            action = ('account', 'action_invoice_tree1')
        elif nfe.infNFe.ide.tpNF.valor == 1:
            action = ('account', 'action_invoice_tree2')

        self.nfe = nfe
        # TODO Buscar o protocolo da nota
        self.protNFe = ProtNFe()
        nfref = self._get_NFRef()
        nfref.xml = nfe.xml
        self.nfref = nfref

        self.dup = self._get_Dup()
        self.dup.xml = nfe.xml

        pool = pooler.get_pool(cr.dbname)
        invoice_obj = pool.get('account.invoice')

        try:
            nfe_references = self._get_nfe_references(
                cr, uid, pool, context=context)
            fiscal_doc_obj = pool.get(
                'l10n_br_account_product.document.related')
            fiscal_doc_id = fiscal_doc_obj.create(cr, uid, nfe_references)
        except AttributeError:
            pass

        invoice_vals = {
            'issuer': '1'
        }

        carrier_data = self._get_carrier_data(cr, uid, pool, context=context)
        in_out_data = self._get_in_out_adress(cr, uid, pool, context=context)
        receiver = self._get_receiver(cr, uid, pool, context=context)
        nfe_identification = self._get_nfe_identification(
            cr, uid, pool, context=context)

        emmiter = self._get_emmiter(cr, uid, pool, context=context)
        encashment_data = self._get_encashment_data(
            cr, uid, pool, context=context)

        adittional = self._get_additional_information(
            cr,
            uid,
            pool,
            context=context)
        weight_data = self._get_weight_data(cr, uid, pool, context=context)
        protocol = self._get_protocol(cr, uid, pool, context=context)
        total = self._get_total(cr, uid, context=context)

        invoice_vals.update(carrier_data)
        invoice_vals.update(in_out_data)
        invoice_vals.update(receiver)
        invoice_vals.update(nfe_identification)
        invoice_vals.update(emmiter)
        invoice_vals.update(encashment_data)
        invoice_vals.update(adittional)
        invoice_vals.update(weight_data)
        invoice_vals.update(total)

        inv_line_ids = []
        for det in self.nfe.infNFe.det:
            self.det = det
            inv_line_ids += self._get_details(cr, uid, pool, context=context)

        invoice_vals['invoice_line'] = inv_line_ids

        return invoice_vals, action

    def _get_nfe_identification(self, cr, uid, pool, context=None):
        # Identificação da NF-e
        #
        res = {}

        fiscal_doc_ids = pool.get('l10n_br_account.fiscal.document').search(
            cr, uid, [('code', '=', self.nfe.infNFe.ide.mod.valor)])

        res['fiscal_document_id'] = \
            fiscal_doc_ids[0] if fiscal_doc_ids else False

        res['vendor_serie'] = self.nfe.infNFe.ide.serie.valor
        res['number'] = self.nfe.infNFe.ide.nNF.valor
        res['internal_number'] = self.nfe.infNFe.ide.nNF.valor
        res['date_in_out'] = datetime.now()
        res['nfe_purpose'] = str(self.nfe.infNFe.ide.finNFe.valor)
        res['nfe_access_key'] = self.nfe.infNFe.Id.valor
        res['nat_op'] = self.nfe.infNFe.ide.natOp.valor
        res['ind_final'] = self.nfe.infNFe.ide.indFinal.valor
        res['ind_pres'] = self.nfe.infNFe.ide.indPres.valor
        res['date_hour_invoice'] = self.nfe.infNFe.ide.dhEmi.valor
        res['nfe_version'] = '3.10'
        return res

        res['type'] = 'in_invoice'  # Fixo por hora - apenas nota de entrada
        return res

    def _get_in_out_adress(self, cr, uid, pool, context=None):

        if self.nfe.infNFe.ide.tpNF.valor == '0':
            cnpj = self._mask_cnpj_cpf(
                True,
                self.nfe.infNFe.retirada.CNPJ.valor)
        else:
            cnpj = self._mask_cnpj_cpf(
                True,
                self.nfe.infNFe.entrega.CNPJ.valor)

        partner_ids = pool.get('res.partner').search(
            cr, uid, [('cnpj_cpf', '=', cnpj)])

        return {'partner_shipping_id': partner_ids[
            0] if partner_ids else False}

    def _get_nfe_references(self, cr, uid, pool, context=None):

        #
        # Documentos referenciadas
        #
        nfe_reference = {}
        state_obj = pool.get('res.country.state')
        fiscal_doc_obj = pool.get('l10n_br_account_product.fiscal.document')

        if self.nfref.refNF.CNPJ.valor:

            state_ids = state_obj.search(cr, uid, [
                ('ibge_code', '=', self.nfref.refNF.cUF.valor)])

            fiscal_doc_ids = fiscal_doc_obj.search(cr, uid, [
                ('code', '=', self.nfref.refNF.mod.valor)])

            nfe_reference.update({
                'document_type': 'nf',
                'state_id': state_ids[0] if state_ids else False,
                'date': self.nfref.refNF.AAMM.valor or False,
                'cnpj_cpf': self._mask_cnpj_cpf(True, self.nfref.refNF.CNPJ.valor) or False,
                'fiscal_document_id': fiscal_doc_ids[0] if fiscal_doc_ids
                else False,
                'serie': self.nfref.refNF.serie.valor or False,
                'internal_number': self.nfref.refNF.nNF.valor or False,
            })

        elif self.nfref.refNFP.CNPJ.valor:

            state_ids = state_obj.search(cr, uid, [
                ('ibge_code', '=', self.nfref.refNFP.cUF.valor)])
            fiscal_doc_ids = fiscal_doc_obj.search(cr, uid, [
                ('code', '=', self.nfref.refNFP.mod.valor)])

            cnpj = self._mask_cnpj_cpf(True, self.nfref.refNFP.CNPJ.valor)
            cpf = self._mask_cnpj_cpf(False, self.nfref.refNFP.CPF.valor)
            cnpj_cpf = (cnpj or cpf)

            nfe_reference.update({
                'document_type': 'nfrural',
                'state_id': state_ids[0] if state_ids else False,
                'date': self.nfref.refNFP.AAMM.valor,
                'inscr_est': self.nfref.refNFP.IE.valor,
                'fiscal_document_id': fiscal_doc_ids[0] if fiscal_doc_ids
                else False,
                'serie': self.nfref.refNFP.serie.valor,
                'internal_number': self.nfref.refNFP.nNF.valor,
                'cnpj_cpf': cnpj_cpf,
            })
        elif self.nfref.refNFe.valor:
            nfe_reference.update({
                'document_type': 'nfe',
                'access_key': self.nfref.refNFe.valor,
            })
        elif self.nfref.refCTe.valor:
            nfe_reference.update({
                'document_type': 'cte',
                'access_key': self.nfref.refCTe.valor,
            })
        elif self.nfref.refECF:
            fiscal_document_ids = \
                pool.get('l10n_br_account.fiscal.document').search(
                    cr, uid, [('code', '=', self.nfref.refECF.mod.valor)])

            nfe_reference.update({
                'document_type': 'cf',
                'fiscal_document_id': fiscal_document_ids[0] if
                fiscal_document_ids else False,
                'serie': self.nfref.refNF.serie.valor,
                'internal_number': self.nfref.refNF.nNF.valor,
            })

        return nfe_reference

    def _get_emmiter(self, cr, uid, pool, context=None):
        #
        # Emitente da nota é o fornecedor
        #
        # TODO - Tratar mascara do ZIP e Inscricao Estadual
        emitter = {}

        cnpj_cpf = ''

        if self.nfe.infNFe.emit.CNPJ.valor:
            cnpj_cpf = self._mask_cnpj_cpf(
                True,
                self.nfe.infNFe.emit.CNPJ.valor)

        elif self.nfe.infNFe.emit.CPF.valor:
            cnpj_cpf = self._mask_cnpj_cpf(False,
                                           self.nfe.infNFe.emit.CPF.valor)
        receiver_partner_ids = pool.get('res.partner').search(
            cr, uid, [('cnpj_cpf', '=', cnpj_cpf)])

        # Quando o cliente é estrangeiro, ele nao possui cnpj. Por isso
        # realizamos a busca usando como chave de busca o nome da empresa ou
        # a sua razao social
        if not receiver_partner_ids:
            aux = ['|',
                   ('name', '=', self.nfe.infNFe.emit.xFant.valor),
                   ('legal_name', '=', self.nfe.infNFe.emit.xNome.valor)]
            receiver_partner_ids = pool.get('res.partner').search(
                cr, uid, aux)

        if len(receiver_partner_ids) > 0:
            emitter['partner_id'] = receiver_partner_ids[0]
            partner = pool.get('res.partner').browse(
                cr,
                uid,
                receiver_partner_ids[0])
            # Busca conta de pagamento do fornecedor
            emitter['account_id'] = partner.property_account_payable.id
        else:  # Retorna os dados para cadastro posteriormente
            partner = {}

            partner['is_company'] = True
            partner[
                'name'] = self.nfe.infNFe.emit.xFant.valor or self.nfe.infNFe.emit.xNome.valor
            partner['legal_name'] = self.nfe.infNFe.emit.xNome.valor
            partner['cnpj_cpf'] = cnpj_cpf
            partner['inscr_est'] = self.nfe.infNFe.emit.IE.valor
            partner['inscr_mun'] = self.nfe.infNFe.emit.IM.valor
            partner['zip'] = self.nfe.infNFe.emit.enderEmit.CEP.valor
            partner['street'] = self.nfe.infNFe.emit.enderEmit.xLgr.valor
            partner['street2'] = self.nfe.infNFe.emit.enderEmit.xCpl.valor
            partner['district'] = self.nfe.infNFe.emit.enderEmit.xBairro.valor
            partner['number'] = self.nfe.infNFe.emit.enderEmit.nro.valor

            city_id = pool.get('l10n_br_base.city').search(
                cr, uid, [('ibge_code', '=', str(self.nfe.infNFe.emit.enderEmit.cMun.valor)[2:]),
                          ('state_id.ibge_code', '=', str(self.nfe.infNFe.emit.enderEmit.cMun.valor)[0:2])])
            if len(city_id) > 0:
                city = pool.get('l10n_br_base.city').browse(
                    cr,
                    uid,
                    city_id[0])
                partner['l10n_br_city_id'] = city_id[0]
                partner['state_id'] = city.state_id.id
                partner['country_id'] = city.state_id.country_id.id

            partner['phone'] = self.nfe.infNFe.emit.enderEmit.fone.valor
            partner['supplier'] = True

            emitter['partner_id'] = False
            emitter['partner_values'] = partner
            emitter['account_id'] = False

        return emitter

    def _get_receiver(self, cr, uid, pool, context=None):
        #
        # Recebedor da mercadoria é a empresa
        #
        receiver = {}
        partner_obj = pool.get('res.partner')
        company_obj = pool.get('res.company')
        cnpj = self._mask_cnpj_cpf(True, self.nfe.infNFe.dest.CNPJ.valor)

        emitter_partner_ids = partner_obj.search(
            cr, uid, [('cnpj_cpf', '=', cnpj)])

        if len(emitter_partner_ids) > 0:
            company_ids = company_obj.search(
                cr, uid, [('partner_id', '=', emitter_partner_ids[0])])
            if len(company_ids) > 0:
                receiver['company_id'] = company_ids[0]
                return receiver

        raise Exception(u'O xml a ser importado foi emitido para o CNPJ {0} - {1}\n'
                        u'o qual não corresponde ao CNPJ cadastrado na empresa\n'
                        u'O arquivo não será importado.'.format(cnpj, self.nfe.infNFe.dest.xNome.valor))

    def _get_details(self, cr, uid, pool, context=None):
        #
        # Detalhes
        #
        # Importamos dados da invoice line
        inv_line = {}

        product_ids = pool.get('product.product').search(
            cr, uid, [('default_code', '=', self.det.prod.cProd.valor)])
        if len(product_ids) == 0:
            product_ids = pool.get('product.product').search(
                cr, uid, [('ean13', '=', self.det.prod.cEAN.valor)])
        if len(product_ids) == 0:
            cnpj_cpf = self._mask_cnpj_cpf(
                True,
                self.nfe.infNFe.emit.CNPJ.valor)
            supplierinfo_ids = pool.get('product.supplierinfo').search(
                cr, uid, ['|', ('name.cnpj_cpf', '=', cnpj_cpf),
                          ('name.cnpj_cpf',
                           '=',
                           self.nfe.infNFe.emit.CNPJ.valor),
                          ('product_code', '=', self.det.prod.cProd.valor)])
            if len(supplierinfo_ids) > 0:
                supplier_info = pool.get('product.supplierinfo').browse(
                    cr,
                    uid,
                    supplierinfo_ids[0])
                inv_line['product_id'] = supplier_info.product_tmpl_id\
                    .product_variant_ids[0].id
                inv_line['name'] = supplier_info.product_tmpl_id\
                    .product_variant_ids[0].name
            else:
                inv_line['product_id'] = False
                inv_line['name'] = ''
        else:
            product_info = pool.get('product.product').browse(
                cr,
                uid,
                product_ids[0])
            inv_line['product_id'] = product_ids[0] if product_ids else False
            inv_line['name'] = product_info.name

        inv_line['product_code_xml'] = self.det.prod.cProd.valor
        inv_line['product_name_xml'] = self.det.prod.xProd.valor

        ncm = self.det.prod.NCM.valor
        ncm = ncm[:4] + '.' + ncm[4:6] + '.' + ncm[6:]
        fc_id = pool.get('account.product.fiscal.classification').search(
            cr, uid, [('name', '=', ncm)]
        )

        inv_line['fiscal_classification_id'] = fc_id[
            0] if len(fc_id) > 0 else False

        cfop_ids = pool.get('l10n_br_account_product.cfop').search(
            cr, uid, [('code', '=', self.det.prod.CFOP.valor)])

        inv_line['cfop_xml'] = self.det.prod.CFOP.valor
        inv_line['cfop_id'] = cfop_ids[0] if len(cfop_ids) > 0 else False

        uom_ids = pool.get('product.uom').search(
            cr, uid, [('name', '=ilike', self.det.prod.uCom.valor)],
            context=context)

        inv_line['ncm_xml'] = ncm
        inv_line['ean_xml'] = self.det.prod.cEAN.valor
        inv_line['uom_xml'] = self.det.prod.uCom.valor
        inv_line['uos_id'] = uom_ids[0] if len(uom_ids) > 0 else False
        if not inv_line['uos_id'] and inv_line['product_id']:
            product = pool['product.product'].browse(
                cr,
                uid,
                inv_line['product_id'])
            inv_line['uos_id'] = product.uom_id.id
        inv_line['quantity'] = float(self.det.prod.qCom.valor)
        inv_line['price_unit'] = float(self.det.prod.vUnCom.valor)
        inv_line['price_gross'] = float(self.det.prod.vProd.valor)

        inv_line['freight_value'] = float(self.det.prod.vFrete.valor)
        inv_line['insurance_value'] = float(self.det.prod.vSeg.valor)
        inv_line['discount_value'] = float(self.det.prod.vDesc.valor)
        inv_line['other_costs_value'] = float(self.det.prod.vOutro.valor)

        # Código do serviço não vai existir se for produto
        if not self.det.imposto.ISSQN.cListServ.valor:
            inv_line['icms_origin'] = str(self.det.imposto.ICMS.orig.valor)

            icms_cst_ids = pool.get('account.tax.code').search(
                cr, uid, [('code', '=', self.det.imposto.ICMS.CST.valor),
                          ('domain', '=', 'icms')])

            inv_line['icms_cst_id'] = icms_cst_ids[
                0] if icms_cst_ids else False
            inv_line['icms_percent'] = self.det.imposto.ICMS.pCredSN.valor
            inv_line['icms_value'] = self.det.imposto.ICMS.vCredICMSSN.valor

            inv_line['icms_base_type'] = str(self.det.imposto.ICMS.modBC.valor)
            inv_line['icms_base'] = self.det.imposto.ICMS.vBC.valor
            inv_line[
                'icms_percent_reduction'] = self.det.imposto.ICMS.pRedBC.valor
            inv_line['icms_percent'] = self.det.imposto.ICMS.pICMS.valor
            inv_line['icms_value'] = self.det.imposto.ICMS.vICMS.valor

            #
            # # ICMS ST
            #
            inv_line['icms_st_base_type'] = str(
                self.det.imposto.ICMS.modBCST.valor)
            inv_line['icms_st_mva'] = self.det.imposto.ICMS.pMVAST.valor
            inv_line[
                'icms_st_percent_reduction'] = self.det.imposto.ICMS.pRedBCST.valor
            inv_line['icms_st_base'] = self.det.imposto.ICMS.vBCST.valor
            inv_line['icms_st_percent'] = self.det.imposto.ICMS.pICMSST.valor
            inv_line['icms_st_value'] = self.det.imposto.ICMS.vICMSST.valor

            #
            # # IPI
            #
            ipi_cst_ids = pool.get('account.tax.code').search(
                cr, uid, [('code', '=', self.det.imposto.IPI.CST.valor),
                          ('domain', '=', 'ipi')])
            if self.det.imposto.IPI.vBC.valor and self.det.imposto.IPI.pIPI.valor:
                inv_line['ipi_type'] = 'percent'
                inv_line['ipi_base'] = self.det.imposto.IPI.vBC.valor
                inv_line['ipi_percent'] = self.det.imposto.IPI.pIPI.valor
                inv_line['ipi_cst_id'] = ipi_cst_ids[
                    0] if ipi_cst_ids else False

            elif self.det.imposto.IPI.qUnid.valor and \
                    self.det.imposto.IPI.vUnid.valor:
                inv_line['ipi_percent'] = self.det.imposto.IPI.vUnid.valor

            else:
                ipi_cst_ids = pool.get('account.tax.code').search(
                    cr, uid, [('code', '=', '49'),
                              ('domain', '=', 'ipi')])
                inv_line['ipi_type'] = 'percent'
                inv_line['ipi_cst_id'] = ipi_cst_ids[
                    0] if ipi_cst_ids else False

            inv_line['ipi_value'] = self.det.imposto.IPI.vIPI.valor

        else:
            #
            # # ISSQN
            #
            inv_line['issqn_base'] = self.det.imposto.ISSQN.vBC.valor
            inv_line['issqn_percent'] = self.det.imposto.ISSQN.vAliq.valor
            inv_line['issqn_value'] = self.det.imposto.ISSQN.vISSQN.valor
            inv_line['issqn_type'] = self.det.imposto.ISSQN.cSitTrib.valor

        # PIS
        pis_cst_ids = pool.get('account.tax.code').search(
            cr, uid, [('code', '=', self.det.imposto.PIS.CST.valor), ('domain', '=', 'pis')])

        inv_line['pis_cst_id'] = pis_cst_ids[0] if pis_cst_ids else False
        inv_line['pis_base'] = self.det.imposto.PIS.vBC.valor
        inv_line['pis_percent'] = self.det.imposto.PIS.pPIS.valor
        inv_line['pis_value'] = self.det.imposto.PIS.vPIS.valor

        # PISST
        inv_line['pis_st_base'] = self.det.imposto.PISST.vBC.valor
        inv_line['pis_st_percent'] = self.det.imposto.PISST.pPIS.valor
        inv_line['pis_st_value'] = self.det.imposto.PISST.vPIS.valor

        # COFINS
        cofins_cst_ids = pool.get('account.tax.code').search(
            cr, uid, [('code', '=', self.det.imposto.COFINS.CST.valor), ('domain', '=', 'cofins')])

        inv_line['cofins_cst_id'] = \
            cofins_cst_ids[0] if cofins_cst_ids else False
        inv_line['cofins_base'] = self.det.imposto.COFINS.vBC.valor
        inv_line['cofins_percent'] = self.det.imposto.COFINS.pCOFINS.valor
        inv_line['cofins_value'] = self.det.imposto.COFINS.vCOFINS.valor

        # COFINSST
        inv_line['cofins_st_base'] = self.det.imposto.COFINSST.vBC.valor
        inv_line['cofins_st_percent'] = self.det.imposto.COFINSST.pCOFINS.valor
        inv_line['cofins_st_value'] = self.det.imposto.COFINSST.vCOFINS.valor

        return [(0, 0, inv_line)]

    def _get_di(self, cr, uid, pool, i, context=None):

        state_ids = pool.search(
            cr, uid, [('code', '=', self.di.UFDesemb.valor)])

        di = {
            'name': self.di.nDI.valor,
            'date_registration': self.di.dDI.valor,
            'location': self.di.xLocDesemb.valor,
            'state_id': state_ids[0] if state_ids else False,
            # self.di.UFDesemb.valor = inv_di.state_id.code or ''
            'date_release': self.di.dDesemb.valor,
            'exporting_code': self.di.cExportador.valor
        }
        return di

    def _get_addition(
            self, cr, uid, ids, inv, inv_line, inv_di, inv_di_line, i, context=None):
        addition = {
            'name': self.di_line.nAdicao.valor,
            'sequence': self.di_line.nSeqAdic.valor,
            'manufacturer_code': self.di_line.cFabricante.valor,
            'amount_discount': self.di_line.vDescDI.valor
        }
        return addition

    def _get_encashment_data(self, cr, uid, pool, context=None):

        #
        # Dados de Cobrança
        #

        # Realizamos a busca da move line a partir do nome da mesma
        # account_move_line_ids = pool.get('account.move.line').search(
        #     cr, uid, [('name', '=', self.dup.nDup.valor)])
        #
        # if not account_move_line_ids:
        #     # Se nao encontrarmos a move line, nos devemos cria-la
        #     vals = {
        #         'name': self.dup.nDup.valor,
        #         'date_maturity': self.dup.dVenc.valor,
        #         'debit': self.dup.vDup.valor,
        #         # 'journal_id': 1,
        #     }
        #
        #     # Inserimos em um lista para que account_move_line_ids continue
        #     # representando uma lista
        #     context['journal_id'] = 1
        #     context['period_id'] = 1
        #     account_move_line_ids = [pool.get('account.move.line').create(
        #         cr, uid, vals, context=context)]
        #
        # encashment_data = {
        #     'move_line_receivable_id': account_move_line_ids[0] if
        #     account_move_line_ids else False,
        #     'date_due': self.dup.dVenc.valor,
        # }

        # Nao conseguimos obter todos os campos necessarios para criacao
        # do account.move.line
        encashment_data = {}
        return encashment_data

    def _get_carrier_data(self, cr, uid, pool, context=None):

        res = {}

        cnpj_cpf = ''

        # Realizamos a importacao da transportadora
        if self.nfe.infNFe.transp.transporta.CNPJ.valor:
            cnpj_cpf = self.nfe.infNFe.transp.transporta.CNPJ.valor
            cnpj_cpf = self._mask_cnpj_cpf(True, cnpj_cpf)

        elif self.nfe.infNFe.transp.transporta.CPF.valor:
            cnpj_cpf = self.nfe.infNFe.transp.transporta.CPF.valor
            cnpj_cpf = self._mask_cnpj_cpf(False, cnpj_cpf)

        carrier_ids = pool.get('delivery.carrier').search(
            cr, uid, [('partner_id.cnpj_cpf', '=', cnpj_cpf)])

        # Realizamos a busca do veiculo pelo numero da placa
        placa = self.nfe.infNFe.transp.veicTransp.placa.valor

        vehicle_ids = pool.get('l10n_br_delivery.carrier.vehicle').search(
            cr, uid, [('plate', '=', placa)])

        # Ao encontrarmos o carrier com o partner especificado, basta
        # retornarmos seu id que o restantes dos dados vem junto
        res['carrier_id'] = carrier_ids[0] if carrier_ids else False
        res['vehicle_id'] = vehicle_ids[0] if vehicle_ids else False

        res['carrier_name'] = self.nfe.infNFe.transp.transporta.xNome.valor
        res['vehicle_plate'] = self.nfe.infNFe.transp.veicTransp.placa.valor

        states = pool.get('res.country.state').search(
            cr, uid, [('code', '=', self.nfe.infNFe.transp.veicTransp.UF.valor),
                      ('country_id', '=', 32)])
        res['vehicle_state_id'] = states[0] if states else False
        return res

    def _get_weight_data(self, cr, uid, pool, context=None):
        #
        # Campos do Transporte da NF-e Bloco 381
        #
        if len(self.nfe.infNFe.transp.vol) > 0:
            weight_data = {
                'number_of_packages': self.nfe.infNFe.transp.vol[0].qVol.valor,
                'kind_of_packages': self.nfe.infNFe.transp.vol[0].esp.valor,
                'brand_of_packages': self.nfe.infNFe.transp.vol[0].marca.valor,
                'notation_of_packages': self.nfe.infNFe.transp.vol[0].nVol.valor,
                'weight': self.nfe.infNFe.transp.vol[0].pesoL.valor,
                'weight_net': self.nfe.infNFe.transp.vol[0].pesoB.valor
            }
            return weight_data
        return {}

    def _get_additional_information(self, cr, uid, pool, context=None):

        #
        # Informações adicionais
        #
        additional_information = {
            'fiscal_comment': self.nfe.infNFe.infAdic.infAdFisco.valor,
            'comment': self.nfe.infNFe.infAdic.infCpl.valor
        }
        return additional_information

    def _get_total(self, cr, uid, context=None):
        #
        # Totais
        #
        total = {
            'icms_base': self.nfe.infNFe.total.ICMSTot.vBC.valor,
            'icms_value': self.nfe.infNFe.total.ICMSTot.vICMS.valor,
            'icms_st_base': self.nfe.infNFe.total.ICMSTot.vBCST.valor,
            'icms_st_value': self.nfe.infNFe.total.ICMSTot.vST.valor,
            'amount_gross': self.nfe.infNFe.total.ICMSTot.vProd.valor,
            'amount_freight': self.nfe.infNFe.total.ICMSTot.vFrete.valor,
            'amount_insurance': self.nfe.infNFe.total.ICMSTot.vSeg.valor,
            'amount_discount': self.nfe.infNFe.total.ICMSTot.vDesc.valor,
            'ii_value': self.nfe.infNFe.total.ICMSTot.vII.valor,
            'ipi_value': self.nfe.infNFe.total.ICMSTot.vIPI.valor,
            'pis_value': self.nfe.infNFe.total.ICMSTot.vPIS.valor,
            'cofins_value': self.nfe.infNFe.total.ICMSTot.vCOFINS.valor,
            'amount_costs': self.nfe.infNFe.total.ICMSTot.vOutro.valor,
            'amount_total': self.nfe.infNFe.total.ICMSTot.vNF.valor,
        }
        return total

    def _get_protocol(self, cr, uid, pool, context=None):
        protocol = {
            'nfe_status': self.protNFe.infProt.cStat.valor + ' - ' + self.protNFe.infProt.xMotivo.valor,
            'nfe_protocol_number': self.protNFe.infProt.nProt.valor,
            'nfe_date': self.protNFe.infProt.dhRecbto.valor,
        }
        return protocol

    def get_NFe(self):

        try:
            from pysped.nfe.leiaute import NFe_310
        except ImportError:
            raise orm.except_orm(
                _(u'Erro!'),
                _(u"Biblioteca PySPED não instalada!"))

        return NFe_310()

    def _get_NFRef(self):

        try:
            from pysped.nfe.leiaute import NFRef_310
        except ImportError:
            raise orm.except_orm(
                _(u'Erro!'),
                _(u"Biblioteca PySPED não instalada!"))

        return NFRef_310()

    def _get_Det(self):

        try:
            from pysped.nfe.leiaute import Det_310
        except ImportError:
            raise orm.except_orm(
                _(u'Erro!'),
                _(u"Biblioteca PySPED não instalada!"))

        return Det_310()

    def _get_DI(self):
        try:
            from pysped.nfe.leiaute import DI_310
        except ImportError:
            raise orm.except_orm(
                _(u'Erro!'),
                _(u"Biblioteca PySPED não instalada!"))
        return DI_310()

    def _get_Addition(self):
        try:
            from pysped.nfe.leiaute import Adi_310
        except ImportError:
            raise orm.except_orm(
                _(u'Erro!'),
                _(u"Biblioteca PySPED não instalada!"))
        return Adi_310()

    def _get_Vol(self):
        try:
            from pysped.nfe.leiaute import Vol_310
        except ImportError:
            raise orm.except_orm(
                _(u'Erro!'),
                _(u"Biblioteca PySPED não instalada!"))
        return Vol_310()

    def _get_Dup(self):

        try:
            from pysped.nfe.leiaute import Dup_310
        except ImportError:
            raise orm.except_orm(
                _(u'Erro!'),
                _(u"Biblioteca PySPED não instalada!"))

        return Dup_310()

    def get_xml(self, cr, uid, ids, nfe_environment, context=None):
        """"""
        result = []
        for nfe in self._serializer(cr, uid, ids, nfe_environment, context):
            result.append({'key': nfe.infNFe.Id.valor, 'nfe': nfe.get_xml()})
        return result

    def parse_edoc(self, filebuffer, ftype):
        filebuffer = base64.standard_b64decode(filebuffer)
        edoc_file = tempfile.NamedTemporaryFile()
        edoc_file.write(filebuffer)
        edoc_file.flush()

        nfe = self.get_NFe()
        nfe.set_xml(nfe_string)

        return [nfe]

    def import_edoc(self, cr, uid, filebuffer, ftype, context):
        edocs = self.parse_edoc(filebuffer, ftype)
        result = []
        for edoc in edocs:
            docid, docaction = self._deserializer(cr, uid, edoc, context)
            result.append({
                'values': docid,
                'action': docaction
            })
        return result

    @staticmethod
    def _mask_cnpj_cpf(is_company, cnpj_cpf):
        if cnpj_cpf:
            val = re.sub('[^0-9]', '', cnpj_cpf)
            if is_company and len(val) == 14:
                cnpj_cpf = "%s.%s.%s/%s-%s" % (val[0:2], val[2:5], val[5:8],
                                               val[8:12], val[12:14])
            elif not is_company and len(val) == 11:
                cnpj_cpf = "%s.%s.%s-%s" % (val[0:3], val[3:6], val[6:9],
                                            val[9:11])

        return cnpj_cpf
