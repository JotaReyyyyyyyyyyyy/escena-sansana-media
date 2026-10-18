"""Presencia de Flopa en la oficina. No contiene credenciales ni publica contenido."""
import contextlib
import json
import os
import threading
import urllib.request
import uuid
from pathlib import Path

URL = 'https://pablojuan-bot.joagivg-tapiens.workers.dev/oficina/api/flopa'


def avisar_publicacion(tipo, resultado):
    """Solo confirma medios publicados. Fallar aquí jamás cambia el resultado de Instagram."""
    if resultado.get('publicado') is not True:
        return True
    identificador = str(resultado.get('id', ''))
    if tipo not in ('historia', 'publicacion', 'carrusel', 'reel') or not identificador.isdigit():
        return False
    try:
        llave = clave()
        if not llave:
            return False
        datos = {'tipo': tipo, 'id': identificador, 'link': resultado.get('link')}
        req = urllib.request.Request(URL + '/aviso', data=json.dumps(datos).encode(), method='POST',
                                     headers={'Content-Type': 'application/json', 'X-Flopa': llave,
                                              'User-Agent': 'flopa-telegram'})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.load(r).get('ok', False)
    except Exception:
        return False


def avisar_local(tipo, resultado):
    """Una publicación local conserva el aviso pendiente si no alcanza a registrarlo."""
    if resultado.get('publicado') is not True:
        return
    try:
        base = Path(os.environ.get('ESCENA_AGENTE', Path.home() / 'Documents/Escena Sansana/agente'))
        carpeta = base / 'avisos-telegram-pendientes'
        identificador = str(resultado.get('id', ''))
        if not identificador.isdigit():
            return
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / (identificador + '.json')
        datos = {'tipo': tipo, 'resultado': resultado}
        temporal = carpeta / (identificador + '-' + uuid.uuid4().hex + '.tmp')
        temporal.write_text(json.dumps(datos), encoding='utf-8')
        temporal.replace(archivo)
        if avisar_publicacion(tipo, resultado):
            archivo.unlink(missing_ok=True)
    except Exception:
        pass


def recuperar_avisos_locales():
    try:
        base = Path(os.environ.get('ESCENA_AGENTE', Path.home() / 'Documents/Escena Sansana/agente'))
        for archivo in (base / 'avisos-telegram-pendientes').glob('*.json'):
            datos = json.loads(archivo.read_text(encoding='utf-8'))
            if avisar_publicacion(datos['tipo'], datos['resultado']):
                archivo.unlink(missing_ok=True)
    except Exception:
        pass


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
