import datetime as dt
import unittest
from respaldo_tobas import CHILE,HORA,elegible


class RespaldoSeguro(unittest.TestCase):
    def setUp(self):
        self.p={'id':'carrusel-tobas-3','estado':'pendiente','tipo':'carrusel','hora':'2026-10-19 12:00'}

    def test_nunca_adelanta(self):
        self.assertFalse(elegible([self.p],HORA-dt.timedelta(seconds=1)))
        self.assertTrue(elegible([self.p],HORA))

    def test_solo_pendiente_aprobada(self):
        for state in ['manual','publicando','revision','publicada','error','solo-prueba']:
            self.assertFalse(elegible([{**self.p,'estado':state}],HORA))
        self.assertFalse(elegible([{**self.p,'hora':'2026-10-20 12:00'}],HORA))
        self.assertFalse(elegible([{**self.p,'id':'historia-pase'}],HORA))
        self.assertFalse(elegible([self.p,self.p],HORA))

    def test_no_recupera_vencida(self):
        self.assertFalse(elegible([self.p],HORA+dt.timedelta(hours=36,seconds=1)))


if __name__=='__main__':
    unittest.main()
