# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sonda de canales de YouTube: comprueba si su feed público de vídeos se puede leer.

Para cada canal (por su @usuario):
  1. Comprueba robots.txt de youtube.com para la página del canal y para el feed.
  2. Abre la página del canal solo para sacar su identificador (channel_id).
  3. Lee el feed público https://www.youtube.com/feeds/videos.xml?channel_id=... y
     cuenta vídeos, fecha del más reciente y una muestra de títulos.

No descarga vídeos ni transcripciones: solo título, fecha y descripción del feed.

Con la variable de entorno YOUTUBE_API_KEY usa en su lugar la API oficial de YouTube:
resuelve el @usuario con channels.list y prueba la lectura de los últimos vídeos.
(El feed público está prohibido en robots.txt de youtube.com.)

Uso:
    python -m pyxis.sonda_youtube CANALES.json SALIDA.json

CANALES.json: {"canales": [{"nombre": ..., "usuario": "@SoloFonseca", "lista": "video", ...}]}
Si un canal ya trae "canal" (el channel_id), no se abre su página.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.parse
from pathlib import Path

from pyxis.sonda_rss import AGENTE, analizar_feed, descargar, robots

BASE = "https://www.youtube.com"
FEED = BASE + "/feeds/videos.xml?channel_id="
RE_CANAL = [
    re.compile(r"feeds/videos\.xml\?channel_id=(UC[\w-]{22})"),
    re.compile(r'"externalId"\s*:\s*"(UC[\w-]{22})"'),
    re.compile(r'<meta itemprop="(?:channelId|identifier)" content="(UC[\w-]{22})"'),
    re.compile(r'"channelId"\s*:\s*"(UC[\w-]{22})"'),
]
PAUSA = 2.0


def canal_en_pagina(html: str) -> str | None:
    for patron in RE_CANAL:
        m = patron.search(html)
        if m:
            return m.group(1)
    return None


API_CANALES = "https://www.googleapis.com/youtube/v3/channels"


def sondear_api(c: dict, clave: str) -> dict:
    from pyxis.recolector import leer_youtube
    r = {k: c[k] for k in c}
    canal = c.get("canal")
    if not canal:
        usuario = c["usuario"] if c["usuario"].startswith("@") else "@" + c["usuario"]
        url = API_CANALES + "?" + urllib.parse.urlencode({"part": "id,snippet", "forHandle": usuario, "key": clave})
        codigo, _, cuerpo, error = descargar(url)
        if error or not cuerpo:
            r["veredicto"] = f"API: error al buscar el canal ({(error or str(codigo)).replace(clave, '***')})"
            return r
        items = json.loads(cuerpo).get("items", [])
        if not items:
            r["veredicto"] = "API: no existe un canal con ese @usuario"
            # Propuestas por nombre (search.list cuesta 100 unidades: solo en este caso)
            url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(
                {"part": "snippet", "type": "channel", "q": c["nombre"], "maxResults": 5, "key": clave})
            codigo, _, cuerpo, error = descargar(url)
            if cuerpo and not error:
                r["propuestas"] = [
                    {"canal": i["snippet"]["channelId"], "titulo": i["snippet"]["title"],
                     "descripcion": i["snippet"].get("description", "")[:150]}
                    for i in json.loads(cuerpo).get("items", [])]
            return r
        canal = items[0]["id"]
        r["titulo_canal"] = items[0].get("snippet", {}).get("title")
    r["canal"] = canal
    entradas, error = leer_youtube({"canal": canal})
    if error:
        r["veredicto"] = f"API: {error}"
        return r
    fechas = sorted(e["fecha"] for e in entradas if e["fecha"])
    r["entradas"] = len(entradas)
    r["mas_reciente"] = fechas[-1] if fechas else None
    r["muestra"] = [e["titulo"] for e in entradas[:3]]
    r["veredicto"] = "util" if entradas else "sin_videos"
    return r


def sondear(c: dict, rp) -> dict:
    r = {k: c[k] for k in c}
    canal = c.get("canal")
    if not canal:
        usuario = c["usuario"] if c["usuario"].startswith("@") else "@" + c["usuario"]
        pagina = BASE + "/" + urllib.parse.quote(usuario)
        if rp is not None and not rp.can_fetch(AGENTE, pagina):
            r["veredicto"] = "robots.txt no permite abrir la página del canal"
            return r
        codigo, _, cuerpo, error = descargar(pagina)
        if error or not cuerpo:
            r["veredicto"] = f"página del canal no accesible ({error or codigo})"
            return r
        canal = canal_en_pagina(cuerpo.decode("utf-8", errors="replace"))
        if not canal:
            r["veredicto"] = "no se encontró el identificador del canal"
            return r
        time.sleep(PAUSA)
    r["canal"] = canal
    feed = FEED + canal
    if rp is not None and not rp.can_fetch(AGENTE, feed):
        r["veredicto"] = "robots.txt no permite leer el feed"
        return r
    codigo, _, cuerpo, error = descargar(feed)
    if error or not cuerpo:
        r["veredicto"] = f"feed no accesible ({error or codigo})"
        return r
    analisis = analizar_feed(cuerpo)
    if analisis is None:
        r["veredicto"] = "la respuesta no es un feed"
        return r
    r["feed"] = feed
    r.update(analisis)
    horas = analisis.get("horas_desde_la_ultima")
    r["veredicto"] = "util" if horas is not None and horas <= 24 * 30 else "antiguo"
    return r


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sonda de canales de YouTube de Pyxis.")
    p.add_argument("canales")
    p.add_argument("salida")
    a = p.parse_args(argv)
    canales = json.loads(Path(a.canales).read_text(encoding="utf-8"))["canales"]
    clave = os.environ.get("YOUTUBE_API_KEY")
    if clave:
        rp, estado_robots = None, "no aplica: se usa la API oficial"
    else:
        rp, estado_robots = robots(BASE)
    print(f"robots.txt de youtube.com: {estado_robots}", flush=True)
    resultados = []
    for c in canales:
        r = sondear_api(c, clave) if clave else sondear(c, rp)
        resultados.append(r)
        print(f"{c['nombre']:<34} {r['veredicto']:<12} vídeos={r.get('entradas', '-'):<3} "
              f"último={r.get('mas_reciente', '-')}", flush=True)
        time.sleep(PAUSA)
    salida = {
        "ejecutado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "robots": estado_robots,
        "canales": resultados,
    }
    Path(a.salida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.salida).write_text(json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    utiles = sum(r["veredicto"] == "util" for r in resultados)
    print(f"\n{utiles} de {len(resultados)} canales con feed útil.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
