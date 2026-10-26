import datetime as dt
import unittest
from respaldo_hora import CHILE,elegible

HORA=dt.datetime(2026,10,23,19,0,tzinfo=CHILE)


class RespaldoHoraSeguro(unittest.TestCase):
    def setUp(self):
        self.p={'id':'historia-pase','estado':'pendiente','tipo':'historia','hora':'2026-10-23 19:00'}

    def test_nunca_adelanta(self):
        self.assertFalse(elegible([self.p],'historia-pase','2026-10-23 19:00',HORA-dt.timedelta(seconds=1)))
        self.assertTrue(elegible([self.p],'historia-pase','2026-10-23 19:00',HORA))

    def test_historia_por_telegram_activa_el_envio_a_su_hora(self):
        p={**self.p,'tipo':'historia-telegram'}
        self.assertTrue(elegible([p],'historia-pase','2026-10-23 19:00',HORA))

    def test_solo_pendiente_aprobada(self):
        for state in ['manual','publicando','revision','publicada','error','solo-prueba','cancelada']:
            self.assertFalse(elegible([{**self.p,'estado':state}],'historia-pase','2026-10-23 19:00',HORA))
        self.assertFalse(elegible([{**self.p,'tipo':'historia-musica'}],'historia-pase','2026-10-23 19:00',HORA))
        self.assertFalse(elegible([self.p],'historia-arte','2026-10-23 19:00',HORA))
        self.assertFalse(elegible([self.p,self.p],'historia-pase','2026-10-23 19:00',HORA))

    def test_ignora_pieza_reprogramada(self):
        movida={**self.p,'hora':'2026-10-25 19:00'}
        self.assertFalse(elegible([movida],'historia-pase','2026-10-23 19:00',HORA))

    def test_no_recupera_vencida(self):
        self.assertFalse(elegible([self.p],'historia-pase','2026-10-23 19:00',HORA+dt.timedelta(hours=36,seconds=1)))


if __name__=='__main__':
    unittest.main()
