'''
Created on 29 de out de 2015

@author: danimar
'''

from openerp import api, models


class DanfseReport(models.AbstractModel):
    _name = 'report.nfse_sao_paulo.danfse_report'

    @api.multi
    def render_html(self, data=None):        
        print self
        report_obj = self.env['report']
        report = report_obj._get_report_from_name(
            'nfse_sao_paulo.danfse_report')
        
        nfse = {'numero': '00001'}
        
        docargs = {
            'doc_ids': self._ids,
            'doc_model': report.model,
            'docs': self.env[report.model].browse(self._ids),
            'nfse': nfse
        }
        return report_obj.render(
            'nfse_sao_paulo.danfse_report_template', docargs)
