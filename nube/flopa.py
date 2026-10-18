"""Presencia de Flopa en la oficina. No contiene credenciales ni publica contenido."""
import contextlib
import json
import os
import threading
import urllib.request
import uuid
from pathlib import Path

URL = 'https://pablojuan-bot.joagivg-tapiens.workers.dev/oficina/api/flopa'


def clave():
    valor = os.environ.get('FLOPA_KEY', '').strip()
    if valor:
        return valor
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        return ''
    archivo = Path.home() / 'Documents/PabloJuan/secretos.txt'
    try:
        for linea in archivo.read_text(encoding='utf-8').splitlines():
            if linea.startswith('FLOPA_KEY='):
                return linea.split('=', 1)[1].strip()
    except OSError:
        pass
    return ''


def reportar(accion, operacion, tarea=None, resultado=None):
    try:
        llave = clave()
        if not llave:
            return False
        datos = {'accion': accion, 'operacion': operacion, 'tarea': tarea, 'resultado': resultado}
        req = urllib.request.Request(URL, data=json.dumps(datos).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'X-Flopa': llave,
                                              'User-Agent': 'flopa-oficina'})
        with urllib.request.urlopen(req, timeout=2) as r:
            return json.load(r).get('ok', False)
    except Exception:
        # La presencia es accesoria y nunca cambia el resultado de una publicación.
        return False


@contextlib.contextmanager
def actividad(tarea, terminado='Terminó una tarea de Escena Sansana'):
    operacion = uuid.uuid4().hex
    detener = threading.Event()
    reportar('inicio', operacion, tarea)

    def latir():
        while not detener.wait(30):
            reportar('latido', operacion, tarea)

    hilo = threading.Thread(target=latir, daemon=True)
    hilo.start()
    resultado = terminado
    try:
        yield
    except BaseException:
        resultado = 'La tarea de Escena Sansana terminó con un error o fue interrumpida'
        raise
    finally:
        detener.set()
        hilo.join(timeout=3)
        reportar('fin', operacion, tarea, resultado)
