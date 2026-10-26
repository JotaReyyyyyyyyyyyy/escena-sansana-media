# -*- coding: utf-8 -*-
"""
nube/publicar.py — publica en @escena_sansana lo que toca segun nube/cola.json.

Lo corre GitHub Actions cada 10 minutos (.github/workflows/publicar.yml), sin el PC.
Cada pieza de la cola ya fue aprobada por Joaquin en el chat antes de entrar aqui.

    IG_TOKEN=... python nube/publicar.py            publica lo vencido
    IG_TOKEN=... PRUEBA=true python nube/publicar.py  arma todo sin publicar

Las historias no van a Instagram por aqui: las sube Joaquin desde la app con su cancion.
A su hora (tipo historia-telegram), Flopa le manda el archivo y la cancion por Telegram.

Las fotos y videos viven en nube/media/<id>/ de este repo publico: Instagram los
descarga desde raw.githubusercontent.com. Despues de publicar, el estado se guarda en
la cola con un commit al tiro, para que la siguiente corrida no la repita.
"""
import datetime as dt
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

from flopa import actividad, avisar_publicacion, clave

RAIZ = Path(__file__).resolve().parent
COLA = RAIZ / "cola.json"
REPO = os.environ.get("GITHUB_REPOSITORY", "JotaReyyyyyyyyyyyy/escena-sansana-media")
RAMA = os.environ.get("GITHUB_REF_NAME", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{RAMA}/nube/media/"
GRAPH = "https://graph.instagram.com/"
UID = "17841475030219124"  # @escena_sansana
CHILE = ZoneInfo("America/Santiago")
VENCE = dt.timedelta(hours=36)  # mas atrasada que esto no se publica (se marca vencida)
LIMITE = {4, 17, 32, 613}
PRUEBA = os.environ.get("PRUEBA", "").lower() == "true"
ENTREGA = "https://pablojuan-bot.joagivg-tapiens.workers.dev/oficina/api/flopa/entrega"


def api(metodo, ruta, **params):
    params["access_token"] = os.environ["IG_TOKEN"].strip()
    datos = urllib.parse.urlencode(params).encode()
    url = GRAPH + ruta
    for intento in range(6):
        req = (urllib.request.Request(url, data=datos, method="POST") if metodo == "POST"
               else urllib.request.Request(url + "?" + datos.decode()))
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            err = json.loads(e.read() or b"{}").get("error", {})
            msg = err.get("error_user_msg") or err.get("message") or str(err)
            if (err.get("code") in LIMITE or err.get("is_transient") or e.code >= 500) and intento < 5:
                print(f"  Instagram pide esperar ({msg[:80]}); reintento en {45 * (intento + 1)} s")
                time.sleep(45 * (intento + 1))
                continue
            raise RuntimeError(f"Instagram {e.code} (codigo {err.get('code')}): {msg}")
        except urllib.error.URLError as e:
            if intento < 5:
                time.sleep(10)
                continue
            raise RuntimeError(f"Sin conexion con Instagram: {e.reason}")


def esperar(cid, video):
    limite = time.time() + (900 if video else 300)
    time.sleep(10 if video else 4)
    while time.time() < limite:
        s = api("GET", cid, fields="status_code,status")
        if s.get("status_code") == "FINISHED":
            return
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram no pudo procesar el archivo: {s.get('status')}")
        time.sleep(15 if video else 8)
    raise RuntimeError("Instagram se demoro demasiado procesando el archivo")


def contenedor(url, tipo, caption=None, portada=None, item=False, colab=None):
    es_video = url.lower().endswith((".mp4", ".mov"))
    p = {}
    if tipo == "historia":
        p["media_type"] = "STORIES"
        p["video_url" if es_video else "image_url"] = url
    elif item:
        p["is_carousel_item"] = "true"
        p.update({"media_type": "VIDEO", "video_url": url} if es_video else {"image_url": url})
    elif es_video:
        p.update(media_type="REELS", video_url=url, share_to_feed="true")
        if portada:
            p["cover_url"] = portada
    else:
        p["image_url"] = url
    if caption:
        p["caption"] = caption
    if colab:
        p["collaborators"] = json.dumps(colab)
    cid = api("POST", f"{UID}/media", **p)["id"]
    esperar(cid, es_video)
    return cid


def lanzar(cid):
    if PRUEBA:
        return {"contenedor": cid, "publicado": False}
    mid = api("POST", f"{UID}/media_publish", creation_id=cid)["id"]
    try:  # desde aqui ya esta publicada: nada puede marcarla como fallida
        link = api("GET", mid, fields="permalink").get("permalink")
    except Exception:
        link = None
    return {"id": mid, "link": link, "publicado": True}


def tipo_aviso(p):
    return "historia" if p["tipo"] == "historia-musica" else p["tipo"]


def publicar(p):
    def anotar(resultado):
        if resultado.get('publicado') is True:
            # También conservar éxitos parciales si falla otra historia del lote.
            p.setdefault('resultados', []).append(resultado)
            resultado['aviso_pendiente'] = not avisar_publicacion(tipo_aviso(p), resultado)
        return resultado

    def confirmar(cid):
        return anotar(lanzar(cid))

    if p["tipo"] == "historia-musica":
        # La API privada se retiró por riesgo de shadowban: solo se publica por la oficial.
        raise RuntimeError("historia-musica ya no se publica; usa tipo historia sin canción")

    urls = [RAW + f"{p['id']}/{a}" for a in p["archivos"]]
    portada = RAW + f"{p['id']}/{p['portada']}" if p.get("portada") else None
    caption, colab = p.get("texto") or None, p.get("colaboradores") or None
    if p["tipo"] == "carrusel":
        hijos = [contenedor(u, "carrusel", item=True) for u in urls]
        extra = {"caption": caption} if caption else {}
        if colab:
            extra["collaborators"] = json.dumps(colab)
        cid = api("POST", f"{UID}/media", media_type="CAROUSEL", children=",".join(hijos), **extra)["id"]
        esperar(cid, False)
        return [confirmar(cid)]
    if p["tipo"] == "historia":
        return [confirmar(contenedor(u, "historia")) for u in urls]
    return [confirmar(contenedor(urls[0], p["tipo"], caption, portada, colab=colab))]


def entregar(p):
    """Las historias las sube Joaquin: Flopa le manda el archivo y la cancion por Telegram.
    El Worker no repite una entrega ya hecha, asi que reintentar es seguro."""
    llave = clave()
    if not llave:
        raise RuntimeError("Falta FLOPA_KEY; no se pudo mandar la historia a Telegram")
    datos = {"id": p["id"], "hora": p["hora"], "cancion": p["cancion"], "link": p.get("link"),
             "archivos": [RAW + f"{p['id']}/{a}" for a in p["archivos"]]}
    req = urllib.request.Request(ENTREGA, data=json.dumps(datos).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-Flopa": llave,
                                          "User-Agent": "flopa-entregas"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.load(r).get("estado")


def recuperar_avisos(cola):
    if PRUEBA:
        return
    cambio = False
    for p in cola:
        for resultado in p.get('resultados', []):
            if resultado.get('aviso_pendiente') and avisar_publicacion(tipo_aviso(p), resultado):
                resultado['aviso_pendiente'] = False
                cambio = True
    if cambio:
        guardar(cola, 'Confirmar avisos de Flopa en Telegram')


def guardar(cola, mensaje):
    COLA.write_text(json.dumps(cola, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    git = lambda *a: subprocess.run(["git", *a], cwd=RAIZ.parent, check=True, capture_output=True)
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("add", "nube/cola.json")
    git("commit", "-m", mensaje)
    for _ in range(3):
        if subprocess.run(["git", "push"], cwd=RAIZ.parent).returncode == 0:
            return
        git("pull", "--rebase")
    raise RuntimeError("No se pudo guardar el estado en el repo; requiere revision antes de reintentar")


def main():
    cola = json.loads(COLA.read_text(encoding="utf-8"))
    ahora = dt.datetime.now(CHILE)
    print(f"Revision: {ahora.isoformat()} America/Santiago; evento={os.environ.get('EVENTO', 'local')}")
    print("Estados: " + json.dumps({s: sum(p.get('estado') == s for p in cola)
                                    for s in sorted({p.get('estado', '?') for p in cola})}))
    if os.environ.get("AUDITORIA", "").lower() == "true":
        for p in cola:
            if p.get("estado") == "pendiente":
                print(f"Pendiente: {p['id']} -> {p['hora']} America/Santiago")
        print("Auditoria: sin llamadas a Instagram ni cambios en la cola")
        return
    recuperar_avisos(cola)
    if not os.environ.get("IG_TOKEN"):
        sys.exit("Falta el secreto IG_TOKEN; no se publico nada")
    hubo_error = False
    # "espera": aprobada pero aun la publica el PC. "solo-prueba": se arma solo en modo prueba.
    activos = ("pendiente", "solo-prueba") if PRUEBA else ("pendiente",)
    for p in cola:
        if p.get("estado") not in activos:
            continue
        hora = dt.datetime.strptime(p["hora"], "%Y-%m-%d %H:%M").replace(tzinfo=CHILE)
        if hora > ahora:
            continue
        if ahora - hora > VENCE and not PRUEBA:
            p["estado"], p["nota"] = "vencida", f"no corrio a tiempo ({ahora:%Y-%m-%d %H:%M})"
            guardar(cola, f"Vencida: {p['id']}")
            continue
        print(f"== {p['id']} ({p['tipo']}, {p['hora']})")
        if p["tipo"] == "historia-telegram":
            if PRUEBA:
                print("  Prueba: no se manda a Telegram")
                continue
            try:
                with actividad(f"Mandando a Joaquín la historia {p.get('pieza', p['id'])}",
                               "Le mandó una historia a Joaquín por Telegram"):
                    estado = entregar(p)
            except Exception as e:
                print(f"  ERROR al mandar a Telegram (se reintenta en la próxima revisión): {e}")
                hubo_error = True
                continue
            if estado == "enviada":
                p["estado"] = "entregada"
                p["entregada"] = f"{dt.datetime.now(CHILE):%Y-%m-%d %H:%M}"
                guardar(cola, f"Entregada a Joaquín: {p['id']}")
            elif estado == "pendiente":
                print("  Telegram pidió esperar; se reintenta en la próxima revisión")
            else:
                p["estado"], p["nota"] = "revision", f"Telegram: {estado}; confirmar con Joaquín si le llegó"
                guardar(cola, f"Revisar entrega de {p['id']}")
                hubo_error = True
            continue
        if not PRUEBA:
            # Reserva durable ANTES de llamar a Instagram. Una interrupcion deja
            # publicando/revision fuera de los reintentos, nunca otra publicacion.
            p["estado"] = "publicando"
            p["inicio"] = ahora.isoformat()
            guardar(cola, f"Reservar publicacion: {p['id']}")
        try:
            tarea = f"{'Probando' if PRUEBA else 'Publicando'} {p['tipo']}: {p.get('pieza', p['id'])}"
            terminado = 'Terminó una prueba sin publicar' if PRUEBA else f"Publicó {p['tipo']}: {p.get('pieza', p['id'])}"
            with actividad(tarea, terminado):
                res = publicar(p)
        except Exception as e:
            print(f"  ERROR: {e}")
            hubo_error = True
            if not PRUEBA:
                p["intentos"] = p.get("intentos", 0) + 1
                p["nota"] = str(e)[:300]
                p["estado"] = "revision"
                guardar(cola, f"Error al publicar {p['id']}")
            continue
        print("  " + json.dumps(res, ensure_ascii=False))
        if PRUEBA:
            continue
        p["estado"] = "publicada"
        p["publicada"] = f"{dt.datetime.now(CHILE):%Y-%m-%d %H:%M}"
        p["links"] = [r.get("link") for r in res]
        p["resultados"] = res
        guardar(cola, f"Publicada: {p['id']}")
    sys.exit(1 if hubo_error else 0)


if __name__ == "__main__":
    main()
