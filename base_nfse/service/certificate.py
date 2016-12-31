# -*- encoding: utf-8 -*-
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

import os.path
from OpenSSL import crypto


def converte_pfx_pem(pfx_stream, senha):
    try:
        certificado = crypto.load_pkcs12(pfx_stream, senha)

        privada = crypto.dump_privatekey(crypto.FILETYPE_PEM,
                                         certificado.get_privatekey())
        certificado = crypto.dump_certificate(crypto.FILETYPE_PEM,
                                              certificado.get_certificate())
    except Exception as e:
        if len(e.message) == 1 and len(e.message[0]) == 3 and \
                e.message[0][2] == 'mac verify failure':
            raise Exception('Senha inválida')
        raise
    return certificado, privada
