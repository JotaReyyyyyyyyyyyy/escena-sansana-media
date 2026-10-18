# -*- coding: utf-8 -*-
"""
nube/renovar.py — renueva el token de Instagram (60 dias mas) y lo escribe en el archivo
que se le indique, sin imprimirlo. Lo usa .github/workflows/renovar.yml, que despues lo
guarda cifrado como secreto IG_TOKEN del repo.

    IG_TOKEN=... python nube/renovar.py <archivo_salida>
"""
import json
import datetime as dt
import os
import sys
import urllib.parse
import urllib.request
from flopa import actividad

def main():
    with actividad('Renovando la conexión de Instagram de Escena Sansana', 'Renovó la conexión de Instagram'):
        url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
            {"grant_type": "ig_refresh_token", "access_token": os.environ["IG_TOKEN"].strip()})
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                res = json.loads(r.read())
            token = res["access_token"].strip()
            seconds = int(res["expires_in"])
            if not token or seconds <= 0:
                raise ValueError("respuesta incompleta")
        except Exception:
            # HTTPError/URLError pueden contener la URL autenticada. Nunca volcarlas.
            raise SystemExit("No se pudo confirmar la renovacion con Instagram; revisar acceso sin imprimir la respuesta") from None
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(token)
        now = dt.datetime.now(dt.timezone.utc)
        meta = {"renovado_utc": now.isoformat(), "expires_in": seconds,
                "vence_estimado_utc": (now + dt.timedelta(seconds=seconds)).isoformat()}
        if len(sys.argv) > 2:
            with open(sys.argv[2], "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        print(f"Token renovado: expires_in={seconds} ({seconds // 86400} dias). Sin exponer credenciales.")


if __name__ == "__main__":
    main()
