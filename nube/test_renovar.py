"""La evidencia de renovación no contiene credenciales ni presupone la vigencia."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import renovar


class RenovacionSegura(unittest.TestCase):
    def run_refresh(self, response=None, error=None):
        with tempfile.TemporaryDirectory() as tmp:
            token=Path(tmp)/'token'; meta=Path(tmp)/'meta.json'
            output=io.StringIO()
            with patch.dict(os.environ, {'IG_TOKEN':'CREDENCIAL-DE-PRUEBA'}), \
                 patch('sys.argv',['renovar.py',str(token),str(meta)]), \
                 patch.object(renovar,'actividad',lambda *a:contextlib.nullcontext()), \
                 patch.object(renovar.urllib.request,'urlopen') as request, \
                 contextlib.redirect_stdout(output):
                if error:
                    request.side_effect=error
                else:
                    request.return_value.__enter__.return_value.read.return_value=json.dumps(response).encode()
                renovar.main()
            return token.read_text(),json.loads(meta.read_text()),output.getvalue()

    def test_guarda_solo_vigencia_reportada_sin_token_en_evidencia(self):
        token,meta,output=self.run_refresh({'access_token':'SECRETO-NUEVO-PRUEBA','expires_in':123456})
        self.assertEqual(token,'SECRETO-NUEVO-PRUEBA')
        self.assertEqual(meta['expires_in'],123456)
        self.assertNotIn(token,json.dumps(meta)+output)

    def test_no_inventa_sesenta_dias_si_falta_expires_in(self):
        with self.assertRaisesRegex(SystemExit,'No se pudo confirmar'):
            self.run_refresh({'access_token':'SECRETO-NUEVO-PRUEBA'})

    def test_error_de_red_no_expone_url_autenticada(self):
        with self.assertRaises(SystemExit) as raised:
            self.run_refresh(error=RuntimeError('https://example.test?access_token=SECRETO'))
        self.assertNotIn('SECRETO',str(raised.exception))
        self.assertNotIn('https:',str(raised.exception))


if __name__=='__main__':
    unittest.main()
