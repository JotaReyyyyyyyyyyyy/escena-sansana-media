# -*- coding: utf-8 -*-
"""
nube/musica_privada.py — historia con canción del catálogo de Instagram (instagrapi).

La API oficial no pone canciones en historias, así que esta pieza usa la API privada
de la app (instagrapi): busca la canción en el catálogo de Instagram, la pega al PNG
como video de 15 s y manda los datos de música de la app. No es oficial; lo aprobó
Joaquín el 18-10-2026 sabiendo el riesgo para la cuenta.

La sesión viene del secreto IG_PRIVADA_SESION (sesion.json de agente/instagrapi/login.py,
creada con el sessionid que pegó Joaquín). Nunca se imprime.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

CUENTA = "escena_sansana"


def instalar():
    try:
        import instagrapi  # noqa: F401
        import moviepy  # noqa: F401
    except ImportError:
        pip = [sys.executable, "-m", "pip", "install", "--quiet"]
        subprocess.run(pip + ["instagrapi[video]==3.0.26"], check=True)
        subprocess.run(pip + ["--no-deps", "moviepy==2.2.1"], check=True)


def cliente():
    datos = os.environ.get("IG_PRIVADA_SESION", "").strip()
    if not datos:
        raise RuntimeError("Falta el secreto IG_PRIVADA_SESION; no se publico nada")
    instalar()
    from instagrapi import Client
    cl = Client()
    cl.delay_range = [1, 3]
    cl.set_settings(json.loads(datos))
    cl.account_info()  # falla aquí, antes de publicar, si la sesión ya no sirve
    return cl


def elegir(cl, p):
    artista = p.get("cancion_artista", "").lower()
    titulo = p.get("cancion_titulo", "").lower()
    for t in cl.search_music(p["cancion_buscar"]):
        if artista in (t.display_artist or "").lower() and titulo in (t.title or "").lower():
            return t
    raise RuntimeError(f"La cancion no aparecio en Instagram: {p['cancion_buscar']}")


def publicar_historia(p, png, prueba=False):
    cl = cliente()
    tema = elegir(cl, p)
    cancion = f"{tema.title} — {tema.display_artist}"
    if prueba:
        return {"publicado": False, "cancion": cancion}
    historia = cl.photo_upload_to_story_with_music(Path(png), "", tema, duration=15.0)
    return {"id": str(historia.pk), "link": f"https://www.instagram.com/stories/{CUENTA}/{historia.pk}",
            "publicado": True, "cancion": cancion}
