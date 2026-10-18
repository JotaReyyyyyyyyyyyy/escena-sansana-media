"""Avisos de Flopa: pruebas sin red, sin Instagram y sin Telegram real."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import flopa
import publicar as motor


class Avisos(unittest.TestCase):
    def test_contenedor_de_prueba_no_notifica(self):
        with patch.object(flopa.urllib.request, 'urlopen') as red:
            self.assertTrue(flopa.avisar_publicacion('historia', {'publicado':False,'contenedor':'1'}))
            red.assert_not_called()
        with patch.object(motor,'PRUEBA',True), patch.object(motor,'avisar_publicacion') as aviso, \
             patch.object(motor,'contenedor',return_value='c1'):
            r=motor.publicar({'id':'x','tipo':'historia','archivos':['1.jpg']})
            self.assertFalse(r[0]['publicado'])
            aviso.assert_not_called()

    def test_publicacion_sin_enlace_tambien_notifica(self):
        p={'id':'x','tipo':'historia','archivos':['1.jpg']}
        with patch.object(motor,'lanzar',return_value={'publicado':True,'id':'123','link':None}), \
             patch.object(motor,'contenedor',return_value='c1'), \
             patch.object(motor,'avisar_publicacion',return_value=True) as aviso:
            r=motor.publicar(p)
        aviso.assert_called_once_with('historia',r[0])
        self.assertFalse(r[0]['aviso_pendiente'])

    def test_error_al_avisar_se_recupera_sin_llamar_a_instagram(self):
        p={'id':'x','tipo':'historia','archivos':['1.jpg']}
        with patch.object(motor,'lanzar',return_value={'publicado':True,'id':'123','link':None}), \
             patch.object(motor,'contenedor',return_value='c1'), \
             patch.object(motor,'avisar_publicacion',return_value=False):
            motor.publicar(p)
        self.assertTrue(p['resultados'][0]['aviso_pendiente'])
        with patch.object(motor,'PRUEBA',False), patch.object(motor,'avisar_publicacion',return_value=True), \
             patch.object(motor,'guardar') as guardar, patch.object(motor,'api') as api:
            motor.recuperar_avisos([p])
            api.assert_not_called()
            guardar.assert_called_once()
        self.assertFalse(p['resultados'][0]['aviso_pendiente'])

    def test_fallo_en_segunda_historia_conserva_primera_y_su_aviso(self):
        p={'id':'x','tipo':'historia','archivos':['1.jpg','2.jpg']}
        with patch.object(motor,'lanzar',side_effect=[{'publicado':True,'id':'123'},RuntimeError('error')]), \
             patch.object(motor,'contenedor',return_value='c1'), \
             patch.object(motor,'avisar_publicacion',return_value=False):
            with self.assertRaises(RuntimeError):
                motor.publicar(p)
        self.assertEqual(p['resultados'][0]['id'],'123')
        self.assertTrue(p['resultados'][0]['aviso_pendiente'])

    def test_aviso_local_fallido_se_conserva_y_se_recupera(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{'ESCENA_AGENTE':tmp}), \
             patch.object(flopa,'avisar_publicacion',return_value=False):
            flopa.avisar_local('reel',{'publicado':True,'id':'123'})
            archivo=Path(tmp)/'avisos-telegram-pendientes/123.json'
            self.assertTrue(archivo.exists())
            with patch.object(flopa,'avisar_publicacion',return_value=True):
                flopa.recuperar_avisos_locales()
            self.assertFalse(archivo.exists())

if __name__=='__main__':
    unittest.main()
