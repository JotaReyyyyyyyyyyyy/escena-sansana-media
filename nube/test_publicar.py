"""Pruebas sin red: horario de Chile, historias manuales y reserva contra duplicados."""
import contextlib
import copy
import datetime as dt
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import publicar as motor


class PublicacionSegura(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cola = Path(self.tmp.name) / "cola.json"
        self.now = dt.datetime(2026, 10, 19, 11, 59, tzinfo=motor.CHILE)
        self.items = [
            {"id": "manual", "estado": "manual", "hora": "2026-10-18 19:00"},
            {"id": "carrusel", "estado": "pendiente", "hora": "2026-10-19 12:00", "tipo": "carrusel"},
        ]

    def run_main(self, moment, publish, save=None, audit=False):
        class Clock(dt.datetime):
            @classmethod
            def now(cls, tz=None):
                return moment
        with patch.dict(os.environ, {"IG_TOKEN": "TEST-NO-CREDENTIAL", "GITHUB_ACTIONS": "false",
                                     "AUDITORIA": str(audit).lower()}, clear=False), \
             patch.object(motor, "COLA", self.cola), patch.object(motor.dt, "datetime", Clock), \
             patch.object(motor, "publicar", publish), \
             patch.object(motor, "actividad", lambda *a: contextlib.nullcontext()):
            if save:
                with patch.object(motor, "guardar", save):
                    motor.main()
            else:
                motor.main()

    def write(self):
        self.cola.write_text(json.dumps(self.items), encoding="utf-8")

    def test_no_publica_antes_de_las_12_ni_historias_manuales(self):
        self.write()
        with patch.object(motor, "publicar") as publish:
            with self.assertRaisesRegex(SystemExit, "0"):
                self.run_main(self.now, publish)
            publish.assert_not_called()
        self.assertEqual(json.loads(self.cola.read_text()), self.items)

    def test_publica_una_vez_con_reserva_previa_y_guarda_id(self):
        self.write()
        calls = []
        def publish(p):
            self.assertEqual(json.loads(self.cola.read_text())[1]["estado"], "publicando")
            calls.append(p["id"])
            return [{"id": "media-id", "link": "https://example.test/p", "publicado": True}]
        moment=self.now + dt.timedelta(minutes=1)
        for _ in range(2):
            with self.assertRaisesRegex(SystemExit, "0"):
                self.run_main(moment, publish)
        self.assertEqual(calls, ["carrusel"])
        result=json.loads(self.cola.read_text())
        self.assertEqual(result[0]["estado"], "manual")
        self.assertEqual(result[1]["resultados"][0]["id"], "media-id")

    def test_error_ambiguo_no_reintenta_automaticamente(self):
        self.write()
        calls=[]
        def publish(p):
            calls.append(p["id"])
            raise RuntimeError("respuesta interrumpida despues del envio")
        moment=self.now + dt.timedelta(minutes=1)
        with self.assertRaisesRegex(SystemExit, "1"):
            self.run_main(moment, publish)
        with self.assertRaisesRegex(SystemExit, "0"):
            self.run_main(moment, publish)
        self.assertEqual(calls, ["carrusel"])
        self.assertEqual(json.loads(self.cola.read_text())[1]["estado"], "revision")

    def test_no_publica_si_no_puede_reservar(self):
        self.write()
        def save(*a):
            raise RuntimeError("push rechazado")
        with patch.object(motor, "publicar") as publish:
            with self.assertRaisesRegex(RuntimeError, "push rechazado"):
                self.run_main(self.now + dt.timedelta(minutes=1), publish, save)
            publish.assert_not_called()

    def test_auditoria_sin_publicar_ni_modificar(self):
        self.write()
        before=self.cola.read_bytes()
        with patch.object(motor, "publicar") as publish:
            self.run_main(self.now + dt.timedelta(days=1), publish, audit=True)
            publish.assert_not_called()
        self.assertEqual(self.cola.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
