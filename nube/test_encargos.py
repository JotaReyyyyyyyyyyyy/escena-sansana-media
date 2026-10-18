"""Encargos: IG_TOKEN y la sesión de Claude quedan en etapas separadas. Sin red."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import encargos

APROBADO = {'id': 'a1', 'lease': 'l1', 'estado': 'publicando', 'aprobado': True,
            'vista_enviada': True, 'aprobado_por': 'x', 'tipo': 'historia', 'urls': ['u'], 'texto': ''}
NUEVO = {'id': 'n1', 'lease': 'l2', 'estado': 'pendiente', 'pedido': 'una historia'}


class Etapas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = {'RUNNER_TEMP': self.tmp.name, 'GITHUB_OUTPUT': str(Path(self.tmp.name) / 'out'), 'FLOPA_KEY': 'k'}

    def tearDown(self):
        self.tmp.cleanup()

    def reclamar(self, encargo, **extra):
        with patch.dict(os.environ, {**self.env, **extra}, clear=True), \
             patch.object(encargos, 'api', return_value={'encargo': encargo}), \
             patch.object(encargos, 'resultado'), \
             patch.object(encargos, 'publicar_aprobada') as pub, \
             patch.object(encargos, 'preparar') as prep:
            encargos.reclamar()
        return pub, prep

    def test_reclamar_publica_lo_aprobado_sin_claude(self):
        pub, prep = self.reclamar(APROBADO, IG_TOKEN='t')
        pub.assert_called_once()
        prep.assert_not_called()
        self.assertFalse(encargos.traspaso().exists())

    def test_reclamar_deja_lo_nuevo_para_claude(self):
        pub, prep = self.reclamar(NUEVO, IG_TOKEN='t')
        pub.assert_not_called()
        prep.assert_not_called()
        f = Path(self.tmp.name) / encargos.TRASPASO
        self.assertEqual(json.loads(f.read_text())['id'], 'n1')
        self.assertEqual(f.stat().st_mode & 0o777, 0o600)
        self.assertIn('preparar=true', (Path(self.tmp.name) / 'out').read_text())

    def test_reclamar_rechaza_la_sesion_de_claude(self):
        with patch.dict(os.environ, {**self.env, 'IG_TOKEN': 't', 'CLAUDE_CODE_OAUTH_TOKEN': 'c'}, clear=True), \
             patch.object(encargos, 'api') as red:
            with self.assertRaises(SystemExit):
                encargos.reclamar()
            red.assert_not_called()

    def test_preparar_rechaza_ig_token(self):
        with patch.dict(os.environ, {**self.env, 'IG_TOKEN': 't', 'CLAUDE_CODE_OAUTH_TOKEN': 'c'}, clear=True), \
             patch.object(encargos, 'preparar') as prep:
            with self.assertRaises(SystemExit):
                encargos.preparar_reservado()
            prep.assert_not_called()

    def test_preparar_consume_el_traspaso(self):
        (Path(self.tmp.name) / encargos.TRASPASO).write_text(json.dumps(NUEVO))
        with patch.dict(os.environ, {**self.env, 'CLAUDE_CODE_OAUTH_TOKEN': 'c'}, clear=True), \
             patch.object(encargos, 'resultado'), \
             patch.object(encargos, 'preparar') as prep:
            encargos.preparar_reservado()
        prep.assert_called_once()
        self.assertEqual(prep.call_args[0][0]['id'], 'n1')
        self.assertFalse((Path(self.tmp.name) / encargos.TRASPASO).exists())

    def test_preparar_nunca_publica_un_aprobado(self):
        (Path(self.tmp.name) / encargos.TRASPASO).write_text(json.dumps(APROBADO))
        with patch.dict(os.environ, {**self.env, 'CLAUDE_CODE_OAUTH_TOKEN': 'c'}, clear=True), \
             patch.object(encargos, 'publicar_aprobada') as pub, patch.object(encargos, 'preparar') as prep:
            with self.assertRaises(SystemExit):
                encargos.preparar_reservado()
        pub.assert_not_called()
        prep.assert_not_called()

    def test_entorno_de_claude_sin_credenciales(self):
        with patch.dict(os.environ, {'IG_TOKEN': 't', 'FLOPA_KEY': 'k', 'CLAUDE_CODE_OAUTH_TOKEN': 'c'}, clear=True):
            env = encargos.entorno_claude(Path(self.tmp.name))
        self.assertNotIn('IG_TOKEN', env)
        self.assertNotIn('FLOPA_KEY', env)


if __name__ == '__main__':
    unittest.main()
