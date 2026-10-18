# -*- coding: utf-8 -*-
"""
nube/renovar.py — renueva el token de Instagram (60 dias mas) y lo escribe en el archivo
que se le indique, sin imprimirlo. Lo usa .github/workflows/renovar.yml, que despues lo
guarda cifrado como secreto IG_TOKEN del repo.

    IG_TOKEN=... python nube/renovar.py <archivo_salida>
"""
import json
import os
import sys
import urllib.parse
import urllib.request

url = "https://graph.instagram.com/refresh_access_token?" + urllib.parse.urlencode(
    {"grant_type": "ig_refresh_token", "access_token": os.environ["IG_TOKEN"]})
with urllib.request.urlopen(url, timeout=60) as r:
    res = json.loads(r.read())
with open(sys.argv[1], "w", encoding="utf-8") as f:
    f.write(res["access_token"].strip())
print(f"Token renovado por {int(res.get('expires_in', 5184000)) // 86400} dias")
