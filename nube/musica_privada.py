# -*- coding: utf-8 -*-
"""
nube/musica_privada.py — historia con canción del catálogo de Instagram (instagrapi).

La API oficial no pone canciones en historias, así que esta pieza usa la API privada
de la app (instagrapi): busca la canción en el catálogo de Instagram, la pega al PNG
como video de 15 s y manda los datos de música de la app. No es oficial; lo aprobó
Joaquín el 18-10-2026 sabiendo el riesgo para la cuenta.

La sesión viene del secreto IG_PRIVADA_SESION (sesion.json de agente/instagrapi/login.py,
creada con el sessionid que pegó Joaquín). Este repo y sus logs son públicos, así que:
cada valor de la sesión se tapa en el log de GitHub, los errores salen sin detalle de
Instagram (la nota del error queda en cola.json) y las dependencias se instalan fijas
y con hash desde requisitos_musica.txt.
"""
import json
import logging
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

CUENTA = "escena_sansana"
REQUISITOS = Path(__file__).resolve().parent / "requisitos_musica.txt"
ERRORES = {
    "LoginRequired": "la sesion vencio; Joaquin debe pegar un sessionid nuevo (login.py)",
    "ChallengeRequired": "Instagram pide verificar la cuenta en la app",
    "ChallengeUnknownStep": "Instagram pide verificar la cuenta en la app",
    "ClientNeedsUpgradeError": "Instagram pide actualizar la app emulada (instagrapi)",
    "PleaseWaitFewMinutes": "Instagram pide esperar unos minutos",
    "FeedbackRequired": "Instagram bloqueo la accion por un tiempo",
    "RateLimitError": "Instagram pide esperar (limite de uso)",
}


def error_limpio(e):
    nombre = type(e).__name__
    return RuntimeError(f"{nombre}: {ERRORES.get(nombre, 'error de Instagram; detalle oculto por seguridad')}")


def instalar():
    try:
        import instagrapi  # noqa: F401
        import moviepy  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "--no-deps",
                        "--require-hashes", "-r", str(REQUISITOS)], check=True)


def tapar(cl):
    """Pide a GitHub que oculte en el log público cada valor de la sesión."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return
    auth = cl.settings.get("authorization_data") or {}
    valores = [auth.get("sessionid"), cl.settings.get("mid"), *(cl.settings.get("cookies") or {}).values()]
    try:
        valores.append(cl.authorization)
    except Exception:
        pass
    for v in {str(v) for v in valores if v and len(str(v)) >= 8}:
        for forma in {v, urllib.parse.unquote(v)}:
            if "\n" not in forma:
                print(f"::add-mask::{forma}", flush=True)


def cliente():
    datos = os.environ.get("IG_PRIVADA_SESION", "").strip()
    if not datos:
        raise RuntimeError("Falta el secreto IG_PRIVADA_SESION; no se publico nada")
    instalar()
    for nombre in ("instagrapi", "private_request", "public_request", "graphql_request"):
        logging.getLogger(nombre).setLevel(logging.ERROR)
    from instagrapi import Client
    cl = Client()
    cl.delay_range = [1, 3]
    cl.set_settings(json.loads(datos))
    tapar(cl)
    try:
        cl.account_info()  # falla aquí, antes de publicar, si la sesión ya no sirve
    except Exception as e:
        raise error_limpio(e) from None
    return cl


def elegir(cl, p):
    artista = p.get("cancion_artista", "").lower()
    titulo = p.get("cancion_titulo", "").lower()
    try:
        temas = cl.search_music(p["cancion_buscar"])
    except Exception as e:
        raise error_limpio(e) from None
    for t in temas:
        if artista in (t.display_artist or "").lower() and titulo in (t.title or "").lower():
            return t
    raise RuntimeError(f"La cancion no aparecio en Instagram: {p['cancion_buscar']}")


def publicar_historia(p, png, prueba=False):
    cl = cliente()
    tema = elegir(cl, p)
    cancion = f"{tema.title} — {tema.display_artist}"
    if prueba:
        return {"publicado": False, "cancion": cancion}
    try:
        historia = cl.photo_upload_to_story_with_music(Path(png), "", tema, duration=15.0)
    except Exception as e:  # pudo alcanzar a publicarse: publicar.py la deja en revision
        raise error_limpio(e) from None
    return {"id": str(historia.pk), "link": f"https://www.instagram.com/stories/{CUENTA}/{historia.pk}",
            "publicado": True, "cancion": cancion}
