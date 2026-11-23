# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recolector de Pyxis: guarda los titulares que publican las fuentes.

Lee dos tipos de fuente:
  - «rss»: feeds RSS o Atom que el propio medio publica.
  - «bluesky»: la cuenta pública del medio en Bluesky, a través de su API pública.
  - «portada»: los titulares (enlaces dentro de h1-h3) de la portada del medio, para
    medios sin feed ni cuenta pública; respeta robots.txt y no abre los artículos.
    No hay fecha: se usa la de la primera vez que se ve el titular.
  - «youtube»: los últimos vídeos de un canal, por la API oficial de YouTube (Data API v3),
    con la clave en la variable de entorno YOUTUBE_API_KEY. Las normas de esa API obligan
    a borrar o renovar sus datos a los 30 días: por eso estas entradas van a una carpeta
    aparte (--carpeta-video) que se vacía sola. Sin clave, la fuente se salta.

Respeta robots.txt, no abre artículos y no guarda textos completos: de cada
entrada conserva el titular, el enlace, la fecha y un extracto breve.

Uso:
    python -m pyxis.recolector FUENTES.json CARPETA_SALIDA

FUENTES.json tiene la forma
    {"fuentes": [{"id": "eldiario", "nombre": "elDiario.es", "tipo": "rss",
                  "url": "https://...", "grupo": "izq", "lista": "panel"}, ...]}
(para Bluesky, "tipo": "bluesky" y "cuenta": "reuters.com";
para YouTube, "tipo": "youtube" y "canal": "UC..." con el identificador del canal).

En CARPETA_SALIDA escribe:
  - AAAA/MM/AAAA-MM-DD.jsonl: una entrada por línea, por día de publicación (hora de Madrid).
  - estado.json: resultado de la última ejecución por fuente.
Solo usa la biblioteca estándar de Python.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import time
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

from pyxis.sonda_rss import AGENTE, _fecha, _local, descargar, robots

MADRID = ZoneInfo("Europe/Madrid")
MAX_EXTRACTO = 400  # caracteres
DIAS_DEDUP = 4  # días anteriores que se revisan para no repetir entradas
PAUSA = 1.0
BLUESKY_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/playlistItems"
DIAS_VIDEO = 30  # máximo que permiten las normas de la API de YouTube
RE_URL = re.compile(r"https?://\S+")


def _texto_plano(valor: str, limite: int = MAX_EXTRACTO) -> str:
    texto = re.sub(r"<[^>]+>", " ", html.unescape(valor or ""))
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto if len(texto) <= limite else texto[: limite - 1].rsplit(" ", 1)[0] + "…"


def _iso(f: dt.datetime | None) -> str | None:
    return f.strftime("%Y-%m-%dT%H:%M:%SZ") if f else None


def entradas_feed(cuerpo: bytes) -> list[dict] | None:
    """Extrae titular, enlace, fecha y extracto de un RSS o Atom. None si no es un feed."""
    try:
        raiz = ET.fromstring(cuerpo)
    except ET.ParseError:
        return None
    if _local(raiz.tag) not in ("rss", "feed", "rdf"):
        return None
    salida = []
    for e in raiz.iter():
        if _local(e.tag) not in ("item", "entry"):
            continue
        hijos: dict[str, ET.Element] = {}
        enlaces = []
        for h in e:
            nombre = _local(h.tag)
            hijos.setdefault(nombre, h)
            if nombre == "link":
                enlaces.append(h)
        titulo = _texto_plano(hijos["title"].text or "", 300) if "title" in hijos else ""
        url = None
        for l in enlaces:
            if l.get("href") and l.get("rel", "alternate") == "alternate":
                url = l.get("href")
                break
            if (l.text or "").strip():
                url = l.text.strip()
                break
        if not url and "guid" in hijos and (hijos["guid"].text or "").startswith("http"):
            url = hijos["guid"].text.strip()
        fecha = None
        for clave in ("pubdate", "published", "updated", "date"):
            if clave in hijos:
                fecha = _fecha(hijos[clave].text)
                if fecha:
                    break
        resumen = hijos["description"] if "description" in hijos else hijos.get("summary")
        if resumen is None:  # YouTube y otros: media:group/media:description
            resumen = next((d for d in e.iter() if _local(d.tag) == "description"), None)
        extracto = _texto_plano("".join(resumen.itertext())) if resumen is not None else ""
        if titulo and url:
            salida.append({"titulo": titulo, "url": url, "fecha": _iso(fecha), "extracto": extracto})
    return salida


def entradas_bluesky(datos: dict) -> list[dict]:
    """Convierte la respuesta de getAuthorFeed en entradas. Solo publicaciones propias con enlace."""
    salida = []
    for item in datos.get("feed", []):
        if item.get("reason"):  # republicaciones de otras cuentas
            continue
        post = item.get("post", {})
        registro = post.get("record", {})
        texto = registro.get("text", "")
        externo = (registro.get("embed") or {}).get("external") or {}
        url = externo.get("uri")
        if not url:
            for faceta in registro.get("facets", []) or []:
                for rasgo in faceta.get("features", []):
                    if rasgo.get("uri"):
                        url = rasgo["uri"]
                        break
                if url:
                    break
        if not url:
            m = RE_URL.search(texto)
            url = m.group(0) if m else None
        if not url:
            continue
        titulo = externo.get("title") or RE_URL.sub("", texto).strip()
        salida.append(
            {
                "titulo": _texto_plano(titulo, 300),
                "url": url,
                "fecha": _iso(_fecha(registro.get("createdAt"))),
                "extracto": _texto_plano(externo.get("description") or texto),
            }
        )
    return salida


RUIDO_VIDEO = re.compile(r"https?://|www\.|patrocin|sponsor|suscr[ií]b|subscribe|merch|c[oó]digo|descuento|"
                         r"discount|patreon|instagram|twitter|tiktok|telegram|discord|facebook|linkedin|"
                         r"\bapp\b|enlace|link|únete|join|membres|apoya|support|^\s*#|^\s*\d{1,2}:\d{2}", re.I)


def descripcion_video(texto: str, limite: int = 1000) -> str:
    """Descripción de un vídeo sin enlaces, patrocinios, redes ni marcas de tiempo."""
    texto = html.unescape(texto or "")
    frases = []
    for linea in texto.splitlines():
        if RUIDO_VIDEO.search(linea):  # una línea con enlace o patrocinio se descarta entera
            continue
        for frase in re.split(r"(?<=[.!?])\s+", linea):
            if frase.strip() and not RUIDO_VIDEO.search(frase):
                frases.append(frase.strip())
    return _texto_plano(" ".join(frases), limite)


def entradas_youtube(datos: dict) -> list[dict]:
    """Convierte la respuesta de playlistItems.list en entradas."""
    salida = []
    for item in datos.get("items", []):
        sn = item.get("snippet", {})
        video = (sn.get("resourceId") or {}).get("videoId")
        if not video or not sn.get("title"):
            continue
        salida.append({
            "titulo": _texto_plano(sn["title"], 300),
            "url": f"https://www.youtube.com/watch?v={video}",
            "fecha": _iso(_fecha(sn.get("publishedAt"))),
            "extracto": descripcion_video(sn.get("description", "")),
        })
    return salida


def leer_youtube(f: dict) -> tuple[list[dict], str | None]:
    clave = os.environ.get("YOUTUBE_API_KEY")
    if not clave:
        return [], "sin clave YOUTUBE_API_KEY"
    if not str(f.get("canal", "")).startswith("UC"):
        return [], "falta el identificador del canal"
    lista_subidas = "UU" + f["canal"][2:]
    url = YOUTUBE_API + "?" + urllib.parse.urlencode(
        {"part": "snippet", "playlistId": lista_subidas, "maxResults": 15, "key": clave})
    codigo, _, cuerpo, error = descargar(url)
    if error or not cuerpo:
        return [], (error or f"respuesta vacía (HTTP {codigo})").replace(clave, "***")
    try:
        return entradas_youtube(json.loads(cuerpo)), None
    except json.JSONDecodeError:
        return [], "respuesta de YouTube no válida"


def purgar_video(carpeta: Path, ahora: dt.datetime) -> int:
    """Borra los archivos diarios de vídeo con más de DIAS_VIDEO días."""
    limite = (ahora.astimezone(MADRID) - dt.timedelta(days=DIAS_VIDEO)).date()
    borrados = 0
    for archivo in carpeta.glob("*/*/*.jsonl"):
        try:
            dia = dt.date.fromisoformat(archivo.stem)
        except ValueError:
            continue
        if dia < limite:
            archivo.unlink()
            borrados += 1
    return borrados


class Robots:
    """robots.txt por origen, con caché."""

    def __init__(self) -> None:
        self.cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}

    def permite(self, url: str) -> tuple[bool, str]:
        p = urllib.parse.urlparse(url)
        origen = f"{p.scheme}://{p.netloc}"
        if origen not in self.cache:
            self.cache[origen], _ = robots(origen)
        rp = self.cache[origen]
        if rp is None:
            return True, "robots.txt ilegible: se continúa"
        return rp.can_fetch(AGENTE, url), "robots.txt leído"


class _Titulares(HTMLParser):
    """Recoge enlaces con su texto y si están dentro de (o contienen) un encabezado h1-h3."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.nivel = 0
        self.enlace: str | None = None
        self.con_encabezado = False
        self.texto: list[str] = []
        self.encontrados: list[tuple[str, str, bool]] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("h1", "h2", "h3"):
            self.nivel += 1
            if self.enlace is not None:
                self.con_encabezado = True
        elif tag == "a":
            self.enlace = dict(attrs).get("href") or ""
            self.con_encabezado = self.nivel > 0
            self.texto = []

    def handle_endtag(self, tag):
        if tag in ("h1", "h2", "h3") and self.nivel:
            self.nivel -= 1
        elif tag == "a" and self.enlace is not None:
            self.encontrados.append((self.enlace, " ".join("".join(self.texto).split()), self.con_encabezado))
            self.enlace = None

    def handle_data(self, data):
        if self.enlace is not None:
            self.texto.append(data)


RE_ARTICULO = re.compile(r"/20\d\d/\d\d/\d\d/|\d{6,}|\.html?$")
RE_CHARSET = re.compile(rb"""<meta[^>]+charset=["']?([\w-]+)""", re.I)


def _decodificar(cuerpo: bytes, tipo: str = "") -> str:
    m = re.search(r"charset=([\w-]+)", tipo or "", re.I) or RE_CHARSET.search(cuerpo[:5000])
    codificacion = (m.group(1).decode() if isinstance(m.group(1), bytes) else m.group(1)) if m else "utf-8"
    try:
        return cuerpo.decode(codificacion)
    except (LookupError, UnicodeDecodeError):
        return cuerpo.decode("cp1252", errors="replace")


def entradas_portada(cuerpo: bytes, base: str, maximo: int = 60, tipo: str = "") -> list[dict]:
    """Titulares de una portada: enlaces en encabezados, o a artículos con texto largo."""
    p = _Titulares()
    p.feed(_decodificar(cuerpo, tipo))
    dominio = urllib.parse.urlparse(base).netloc.lower().removeprefix("www.")
    salida, vistas = [], set()
    for href, titulo, con_encabezado in p.encontrados:
        if not href or len(titulo) < 25:
            continue
        url = urllib.parse.urljoin(base, href).split("#")[0]
        partes = urllib.parse.urlparse(url)
        if not partes.netloc.lower().removeprefix("www.").endswith(dominio) or url in vistas:
            continue
        if not con_encabezado and not (len(titulo) >= 40 and RE_ARTICULO.search(partes.path)):
            continue
        vistas.add(url)
        salida.append({"titulo": _texto_plano(titulo, 300), "url": url, "fecha": None, "extracto": ""})
        if len(salida) >= maximo:
            break
    return salida


def leer_fuente(f: dict, rob: Robots) -> tuple[list[dict], str | None]:
    if f["tipo"] == "rss":
        url = f["url"]
    elif f["tipo"] == "youtube":
        return leer_youtube(f)
    elif f["tipo"] == "portada":
        url = f["url"]
    elif f["tipo"] == "bluesky":
        url = BLUESKY_API + "?" + urllib.parse.urlencode({"actor": f["cuenta"], "limit": 50, "filter": "posts_no_replies"})
    else:
        return [], f"tipo desconocido: {f['tipo']}"
    permitido, _ = rob.permite(url)
    if not permitido:
        return [], "robots.txt no lo permite"
    codigo, tipo, cuerpo, error = descargar(url)
    if error or not cuerpo:
        return [], error or f"respuesta vacía (HTTP {codigo})"
    if f["tipo"] == "portada":
        entradas = entradas_portada(cuerpo, url, tipo=tipo)
        return (entradas, None) if entradas else ([], "no se encontraron titulares en la portada")
    if f["tipo"] == "rss":
        entradas = entradas_feed(cuerpo)
        return (entradas, None) if entradas is not None else ([], "la respuesta no es un feed")
    try:
        return entradas_bluesky(json.loads(cuerpo)), None
    except json.JSONDecodeError:
        return [], "respuesta de Bluesky no válida"


def _clave(url: str) -> str:
    p = urllib.parse.urlparse(url)
    limpia = f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}"
    video = urllib.parse.parse_qs(p.query).get("v")  # youtube.com/watch?v=...: el vídeo está en la consulta
    if video:
        limpia += "?v=" + video[0]
    return hashlib.sha1(limpia.encode()).hexdigest()[:16]


def _archivo_dia(salida: Path, dia: dt.date) -> Path:
    return salida / f"{dia:%Y}" / f"{dia:%m}" / f"{dia:%Y-%m-%d}.jsonl"


def recolectar(fuentes: list[dict], salida: Path, salida_video: Path | None = None) -> dict:
    ahora = dt.datetime.now(dt.timezone.utc)
    hoy = ahora.astimezone(MADRID).date()
    salida_video = salida_video or salida
    vistas: set[str] = set()
    for i in range(DIAS_DEDUP + 1):
        for carpeta in {salida, salida_video}:
            archivo = _archivo_dia(carpeta, hoy - dt.timedelta(days=i))
            if archivo.exists():
                for linea in archivo.read_text(encoding="utf-8").splitlines():
                    if linea.strip():
                        vistas.add(json.loads(linea)["id"])
    nuevas: dict[Path, list[dict]] = {}
    estado = []
    rob = Robots()
    limite_antiguedad = ahora - dt.timedelta(days=DIAS_DEDUP)
    ultimo: dict[str, float] = {}  # pausa de cortesía por servidor, no entre servidores distintos
    for f in fuentes:
        host = urllib.parse.urlparse(f.get("url", "")).netloc or f["tipo"]
        espera = PAUSA - (time.monotonic() - ultimo.get(host, -PAUSA))
        if espera > 0:
            time.sleep(espera)
        entradas, error = leer_fuente(f, rob)
        ultimo[host] = time.monotonic()
        n_nuevas = 0
        for e in entradas:
            fecha = dt.datetime.fromisoformat(e["fecha"].replace("Z", "+00:00")) if e["fecha"] else ahora
            if fecha < limite_antiguedad:
                continue
            clave = _clave(e["url"])
            if clave in vistas:
                continue
            vistas.add(clave)
            registro = {
                "id": clave,
                "fuente": f["id"],
                "medio": f["nombre"],
                "grupo": f.get("grupo"),
                "lista": f.get("lista"),
                **({"seccion": f["seccion"]} if f.get("seccion") else {}),
                "via": f["tipo"],
                "recogido": _iso(ahora),
                **e,
            }
            dia = fecha.astimezone(MADRID).date()
            destino = salida_video if f["tipo"] == "youtube" else salida
            nuevas.setdefault(_archivo_dia(destino, dia), []).append(registro)
            n_nuevas += 1
        estado.append(
            {"id": f["id"], "nombre": f["nombre"], "tipo": f["tipo"], "ok": error is None,
             "error": error, "entradas_en_origen": len(entradas), "nuevas": n_nuevas}
        )
        print(f"{f['nombre']:<26} {f['tipo']:<8} {'ok' if error is None else 'ERROR':<6} "
              f"origen={len(entradas):<4} nuevas={n_nuevas:<4} {error or ''}", flush=True)
    for archivo, registros in nuevas.items():
        archivo.parent.mkdir(parents=True, exist_ok=True)
        with archivo.open("a", encoding="utf-8") as fh:
            for r in sorted(registros, key=lambda r: r["fecha"] or ""):
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    purgados = purgar_video(salida_video, ahora) if salida_video != salida else 0
    resumen = {
        "ejecutado": _iso(ahora),
        "video_purgados": purgados,
        "fuentes": len(fuentes),
        "fuentes_ok": sum(e["ok"] for e in estado),
        "entradas_nuevas": sum(e["nuevas"] for e in estado),
        "estado": estado,
    }
    salida.mkdir(parents=True, exist_ok=True)
    (salida / "estado.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return resumen


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Recolector de titulares de Pyxis.")
    p.add_argument("fuentes")
    p.add_argument("salida")
    p.add_argument("--carpeta-video", help="carpeta aparte para las entradas de YouTube (se vacía a los 30 días)")
    a = p.parse_args(argv)
    fuentes = json.loads(Path(a.fuentes).read_text(encoding="utf-8"))["fuentes"]
    r = recolectar(fuentes, Path(a.salida), Path(a.carpeta_video) if a.carpeta_video else None)
    print(f"\n{r['fuentes_ok']} de {r['fuentes']} fuentes leídas; {r['entradas_nuevas']} entradas nuevas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
