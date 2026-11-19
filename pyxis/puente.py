# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Puente entre el recolector y las ediciones: prepara las listas de titulares de una edición.

Lee recoleccion/ (titulares de prensa y análisis) y la rama «video» del repositorio de
datos, filtra por la ventana de la edición y escribe un documento compacto en JSON, con
una lista de texto por grupo de fuentes. Cada línea: «HH:MM | medio | titular | url»
(hora de Madrid; en análisis y vídeo, «DD/MM HH:MM»).

Uso:
    python -m pyxis.puente --edicion manana|mediodia|noche --datos RUTA_PYXIS_DATOS [--salida ARCHIVO]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
# Ventana de novedades (hora de Madrid) y máximo de titulares por medio
EDICIONES = {
    "manana": {"desde": None, "horas": 24, "max": 5},
    "mediodia": {"desde": (8, 30), "max": 4},
    "noche": {"desde": (11, 30), "max": 4},
}
DIAS_LARGOS = 7  # análisis y vídeo: últimos 7 días
MAX_LARGOS = 3   # por medio o canal en análisis y vídeo
MAX_TITULAR = 130


def _leer_jsonl(texto: str) -> list[dict]:
    return [json.loads(l) for l in texto.splitlines() if l.strip()]


def leer_recoleccion(datos: Path, dias: list[dt.date]) -> list[dict]:
    salida = []
    for d in dias:
        archivo = datos / "recoleccion" / f"{d:%Y}" / f"{d:%m}" / f"{d:%Y-%m-%d}.jsonl"
        if archivo.exists():
            salida += _leer_jsonl(archivo.read_text(encoding="utf-8"))
    return salida


def leer_video(datos: Path, dias: list[dt.date]) -> tuple[list[dict], str | None]:
    r = subprocess.run(["git", "-C", str(datos), "fetch", "-q", "origin", "video"], capture_output=True, text=True)
    if r.returncode != 0:
        return [], "no se pudo leer la rama video: " + (r.stderr.strip() or "error de git")[:200]
    salida = []
    for d in dias:
        r = subprocess.run(["git", "-C", str(datos), "show", f"FETCH_HEAD:{d:%Y}/{d:%m}/{d:%Y-%m-%d}.jsonl"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            salida += _leer_jsonl(r.stdout)
    return salida, None


def _fecha(e: dict) -> dt.datetime | None:
    f = e.get("fecha") or e.get("recogido")
    return dt.datetime.fromisoformat(f.replace("Z", "+00:00")) if f else None


def _linea(e: dict, con_dia: bool) -> str:
    f = _fecha(e).astimezone(MADRID)
    hora = f.strftime("%d/%m %H:%M" if con_dia else "%H:%M")
    titular = " ".join(e["titulo"].split())
    if len(titular) > MAX_TITULAR:
        titular = titular[: MAX_TITULAR - 1].rsplit(" ", 1)[0] + "…"
    return f"{hora} | {e['medio']} | {titular} | {e['url']}"


def lista(entradas: list[dict], desde: dt.datetime, maximo: int, con_dia: bool) -> tuple[str, int]:
    por_medio: dict[str, list[dict]] = defaultdict(list)
    for e in entradas:
        f = _fecha(e)
        if f and f >= desde:
            por_medio[e["medio"]].append(e)
    lineas, n = [], 0
    for medio in sorted(por_medio):
        recientes = sorted(por_medio[medio], key=_fecha, reverse=True)[:maximo]
        n += len(recientes)
        lineas += [_linea(e, con_dia) for e in recientes]
    return "\n".join(lineas), n


def preparar(edicion: str, datos: Path, ahora: dt.datetime | None = None) -> dict:
    cfg = EDICIONES[edicion]
    ahora = (ahora or dt.datetime.now(dt.timezone.utc)).astimezone(MADRID)
    hoy = ahora.date()
    if cfg["desde"]:
        desde = ahora.replace(hour=cfg["desde"][0], minute=cfg["desde"][1], second=0, microsecond=0)
    else:
        desde = ahora - dt.timedelta(hours=cfg["horas"])
    desde_largo = ahora - dt.timedelta(days=DIAS_LARGOS)
    dias = [hoy - dt.timedelta(days=i) for i in range(DIAS_LARGOS + 1)]
    todas = leer_recoleccion(datos, dias)
    videos, aviso_video = leer_video(datos, dias)
    doc = {
        "edicion": edicion,
        "fecha": hoy.isoformat(),
        "generado": ahora.strftime("%Y-%m-%d %H:%M"),
        "ventana_desde": desde.strftime("%Y-%m-%d %H:%M"),
        "formato": "Cada línea: hora de Madrid | medio | titular | url. Análisis y vídeo: últimos 7 días, con día.",
        "listas": {},
        "cuentas": {},
    }
    for nombre in ("panel", "extranjero"):
        texto, n = lista([e for e in todas if e.get("lista") == nombre], desde, cfg["max"], False)
        doc["listas"][nombre], doc["cuentas"][nombre] = texto, n
    texto, n = lista([e for e in todas if e.get("lista") == "analisis"], desde_largo, MAX_LARGOS, True)
    doc["listas"]["analisis"], doc["cuentas"]["analisis"] = texto, n
    texto, n = lista(videos, desde_largo, MAX_LARGOS, True)
    doc["listas"]["video"], doc["cuentas"]["video"] = texto, n
    if aviso_video:
        doc["aviso"] = aviso_video
    return doc


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Prepara las listas del recolector para una edición.")
    p.add_argument("--edicion", required=True, choices=sorted(EDICIONES))
    p.add_argument("--datos", required=True, help="carpeta del repositorio pyxis-datos")
    p.add_argument("--salida")
    a = p.parse_args(argv)
    doc = preparar(a.edicion, Path(a.datos))
    texto = json.dumps(doc, ensure_ascii=False, indent=1)
    if a.salida:
        Path(a.salida).write_text(texto + "\n", encoding="utf-8")
    print(f"{a.edicion}: " + ", ".join(f"{k}={v}" for k, v in doc["cuentas"].items())
          + f"; {len(texto.encode())} bytes" + (f"; aviso: {doc['aviso']}" if "aviso" in doc else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
