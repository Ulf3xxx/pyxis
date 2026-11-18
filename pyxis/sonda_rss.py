# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sonda de RSS: comprueba qué medios de un panel ofrecen un feed utilizable.

Para cada medio:
  1. Lee su robots.txt y respeta lo que diga para este agente.
  2. Busca feeds anunciados en la portada (<link rel="alternate" type="application/rss+xml">)
     y prueba algunas rutas habituales (/rss, /feed, /rss.xml...).
  3. Descarga cada feed candidato permitido y mide cuántas entradas trae,
     de cuándo es la más reciente y si incluye extracto o texto.

No abre ni descarga artículos: solo la portada y los feeds, que los medios
publican precisamente para ser leídos por programas.

Uso:
    python -m pyxis.sonda_rss PANEL.json SALIDA.json

PANEL.json debe tener la forma {"medios": [{"nombre": ..., "dominio": ..., "grupo": ...}]}.
Solo usa la biblioteca estándar de Python.
"""
from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from pathlib import Path

AGENTE = "pyxis-sonda/0.0.1 (+https://github.com/Ulf3xxx/pyxis)"
PAUSA = 1.5  # segundos entre peticiones al mismo medio
MAX_FEEDS = 6  # feeds candidatos a probar por medio
RUTAS = ["/rss", "/feed", "/rss.xml", "/feed.xml", "/rss/portada.xml", "/rss/", "/feeds/rss.xml"]
RE_LINK = re.compile(r"<link\b[^>]*>", re.I)
RE_ATTR = re.compile(r'([a-zA-Z-]+)\s*=\s*("([^"]*)"|\'([^\']*)\')')
TIPOS_FEED = ("application/rss+xml", "application/atom+xml", "application/xml", "text/xml")


def descargar(url: str, limite: int = 3_000_000) -> tuple[int | None, str, bytes, str | None]:
    """Devuelve (código HTTP, tipo de contenido, cuerpo, error)."""
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(peticion, timeout=25) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read(limite), None
    except urllib.error.HTTPError as e:
        return e.code, "", b"", f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, "", b"", f"red: {getattr(e, 'reason', e)}"


def robots(base: str) -> tuple[urllib.robotparser.RobotFileParser | None, str]:
    rp = urllib.robotparser.RobotFileParser()
    codigo, _, cuerpo, error = descargar(base + "/robots.txt", 500_000)
    if codigo == 200:
        rp.parse(cuerpo.decode("utf-8", errors="replace").splitlines())
        return rp, "leido"
    if codigo in (401, 403):
        rp.disallow_all = True
        return rp, f"acceso denegado ({codigo}): se trata como prohibido"
    if codigo is not None and 400 <= codigo < 500:
        rp.allow_all = True
        return rp, f"no existe ({codigo}): se trata como permitido"
    return None, f"no se pudo leer ({error})"


def feeds_en_portada(html_portada: str, base: str) -> list[str]:
    encontrados = []
    for etiqueta in RE_LINK.findall(html_portada):
        attrs = {m.group(1).lower(): (m.group(3) if m.group(3) is not None else m.group(4)) for m in RE_ATTR.finditer(etiqueta)}
        if "alternate" in (attrs.get("rel") or "").lower() and (attrs.get("type") or "").lower() in TIPOS_FEED and attrs.get("href"):
            encontrados.append(urllib.parse.urljoin(base + "/", html.unescape(attrs["href"])))
    return list(dict.fromkeys(encontrados))


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _fecha(texto: str | None) -> dt.datetime | None:
    if not texto:
        return None
    texto = texto.strip()
    try:
        f = email.utils.parsedate_to_datetime(texto)
    except (TypeError, ValueError):
        try:
            f = dt.datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return None
    if f.tzinfo is None:
        f = f.replace(tzinfo=dt.timezone.utc)
    return f.astimezone(dt.timezone.utc)


def analizar_feed(cuerpo: bytes) -> dict | None:
    """Analiza un RSS o Atom. Devuelve None si no lo es."""
    try:
        raiz = ET.fromstring(cuerpo)
    except ET.ParseError:
        return None
    if _local(raiz.tag) not in ("rss", "feed", "rdf"):
        return None
    entradas = [e for e in raiz.iter() if _local(e.tag) in ("item", "entry")]
    titulos, fechas, extractos, completos = [], [], 0, 0
    for e in entradas:
        hijos = {_local(h.tag): h for h in e}
        titulos.append((hijos.get("title").text or "").strip() if hijos.get("title") is not None else "")
        for clave in ("pubdate", "published", "updated", "date"):
            if clave in hijos:
                f = _fecha(hijos[clave].text)
                if f:
                    fechas.append(f)
                    break
        resumen = hijos.get("description") or hijos.get("summary")
        texto_resumen = re.sub(r"<[^>]+>", " ", html.unescape("".join(resumen.itertext()))) if resumen is not None else ""
        if len(texto_resumen.split()) >= 15:
            extractos += 1
        contenido = hijos.get("encoded") or hijos.get("content")
        if contenido is not None and len(re.sub(r"<[^>]+>", " ", "".join(contenido.itertext())).split()) >= 150:
            completos += 1
    ahora = dt.datetime.now(dt.timezone.utc)
    return {
        "formato": _local(raiz.tag),
        "entradas": len(entradas),
        "mas_reciente": max(fechas).strftime("%Y-%m-%dT%H:%M:%SZ") if fechas else None,
        "horas_desde_la_ultima": round((ahora - max(fechas)).total_seconds() / 3600, 1) if fechas else None,
        "en_24h": sum(1 for f in fechas if (ahora - f).total_seconds() <= 86400),
        "con_extracto": extractos,
        "con_texto_completo": completos,
        "muestra": [t for t in titulos[:3] if t],
    }


def sondear_medio(m: dict) -> dict:
    dominio = m["dominio"]
    base = "https://" + (dominio if dominio.startswith("www.") else "www." + dominio)
    resultado = {"nombre": m["nombre"], "dominio": dominio, "grupo": m.get("grupo"), "feeds": [], "notas": []}

    rp, estado_robots = robots(base)
    if rp is None:  # algunos medios no usan www
        base = "https://" + dominio
        rp, estado_robots = robots(base)
    resultado["robots"] = estado_robots

    def permitido(url: str) -> bool:
        return True if rp is None else rp.can_fetch(AGENTE, url)

    candidatos: list[tuple[str, str]] = []
    if permitido(base + "/"):
        codigo, _, cuerpo, error = descargar(base + "/")
        resultado["portada"] = error or f"HTTP {codigo}"
        if cuerpo:
            candidatos += [(u, "portada") for u in feeds_en_portada(cuerpo.decode("utf-8", errors="replace"), base)]
    else:
        resultado["portada"] = "robots.txt no permite leerla"
    candidatos += [(base + r, "ruta habitual") for r in RUTAS]

    vistos: set[str] = set()
    for url, origen in candidatos:
        if url in vistos or len(resultado["feeds"]) >= MAX_FEEDS:
            continue
        vistos.add(url)
        if not permitido(url):
            resultado["notas"].append(f"robots.txt no permite {url}")
            continue
        time.sleep(PAUSA)
        codigo, _, cuerpo, error = descargar(url)
        if error or not cuerpo:
            if origen == "portada":
                resultado["notas"].append(f"{url}: {error or 'vacío'}")
            continue
        datos = analizar_feed(cuerpo)
        if datos is None:
            continue
        resultado["feeds"].append({"url": url, "origen": origen, **datos})

    utiles = [f for f in resultado["feeds"] if f["entradas"] and (f["horas_desde_la_ultima"] is None or f["horas_desde_la_ultima"] <= 72)]
    resultado["veredicto"] = (
        "util" if utiles else ("antiguo" if resultado["feeds"] else "sin_feed")
    )
    resultado["con_extracto"] = any(f["con_extracto"] for f in utiles)
    resultado["con_texto_completo"] = any(f["con_texto_completo"] for f in utiles)
    return resultado


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sonda de feeds RSS de un panel de medios.")
    p.add_argument("panel")
    p.add_argument("salida")
    a = p.parse_args(argv)
    medios = json.loads(Path(a.panel).read_text(encoding="utf-8"))["medios"]
    resultados = []
    for m in medios:
        r = sondear_medio(m)
        resultados.append(r)
        mejor = max(r["feeds"], key=lambda f: f["en_24h"], default=None)
        print(
            f"{r['nombre']:<18} {r['veredicto']:<9} feeds={len(r['feeds'])} "
            f"24h={mejor['en_24h'] if mejor else 0:<3} extracto={'sí' if r['con_extracto'] else 'no'} "
            f"robots={r['robots'][:30]} portada={r.get('portada', '')[:25]}",
            flush=True,
        )
    por_grupo: dict[str, dict] = {}
    for r in resultados:
        g = por_grupo.setdefault(r["grupo"] or "sin_grupo", {"medios": 0, "utiles": 0})
        g["medios"] += 1
        g["utiles"] += r["veredicto"] == "util"
    informe = {
        "fuente": "Sonda RSS de Pyxis",
        "generado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "agente": AGENTE,
        "criterio": "«util»: al menos un feed permitido por robots.txt con entradas de las últimas 72 horas.",
        "resumen": {
            "medios": len(resultados),
            "utiles": sum(r["veredicto"] == "util" for r in resultados),
            "antiguos": sum(r["veredicto"] == "antiguo" for r in resultados),
            "sin_feed": sum(r["veredicto"] == "sin_feed" for r in resultados),
            "con_extracto": sum(r["con_extracto"] for r in resultados),
            "por_grupo": por_grupo,
        },
        "medios": resultados,
    }
    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    s = informe["resumen"]
    print(f"\n{s['utiles']} de {s['medios']} medios con feed útil; {s['antiguos']} con feed antiguo; {s['sin_feed']} sin feed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
