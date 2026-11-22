# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Descarga series de mercado de fuentes públicas y dibuja sus gráficas.

Fuentes (todas permiten la descarga automática en su robots.txt):
  - «fred»: Reserva Federal de San Luis (fredgraph.csv, sin clave).
  - «bce»: portal de datos del Banco Central Europeo (data-api.ecb.europa.eu).
  - «bde»: ficheros CSV del Banco de España (www.bde.es); "codigo" es «archivo.csv:SERIE»,
    por ejemplo «ti_1_6.csv:DBLEESI100000000IBDI.B» para el IBEX 35 diario.

Uso:
    python -m pyxis.mercados CONFIG.json CARPETA_DATOS CARPETA_GRAFICAS [--anios 2]

CONFIG.json: {"series": [{"id": "sp500", "fuente": "fred", "codigo": "SP500",
  "titulo": "S&P 500", "unidad": "Puntos", "pie": "...", "fuente_texto": "..."}]}
Escribe CARPETA_DATOS/<id>.csv (fecha,valor), CARPETA_DATOS/resumen.json y
CARPETA_GRAFICAS/<id>.svg (últimos N años).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import time
import urllib.parse
from pathlib import Path

from pyxis.grafica import grafica_svg
from pyxis.recolector import Robots
from pyxis.sonda_rss import descargar

URLS = {
    "fred": "https://fred.stlouisfed.org/graph/fredgraph.csv?id={codigo}",
    "bce": "https://data-api.ecb.europa.eu/service/data/{codigo}?format=csvdata&startPeriod={desde}",
    "bde": "https://www.bde.es/webbe/es/estadisticas/compartido/datos/csv/{archivo}",
}
MESES_BDE = {m: i + 1 for i, m in enumerate(["ENE", "FEB", "MAR", "ABR", "MAY", "JUN",
                                              "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"])}


def parsear_bde(texto: str, serie: str) -> list[tuple[dt.date, float]]:
    """CSV del Banco de España: primera fila con los códigos de serie; filas «DD MES AAAA»."""
    filas = list(csv.reader(io.StringIO(texto)))
    if not filas or serie not in filas[0]:
        return []
    col = filas[0].index(serie)
    salida = []
    for f in filas[1:]:
        partes = f[0].split() if f else []
        if len(partes) != 3 or partes[1] not in MESES_BDE or col >= len(f):
            continue
        try:
            fecha = dt.date(int(partes[2]), MESES_BDE[partes[1]], int(partes[0]))
            salida.append((fecha, float(f[col])))
        except ValueError:
            continue  # día sin dato
    return sorted(salida)


def parsear(fuente: str, texto: str) -> list[tuple[dt.date, float]]:
    filas = list(csv.reader(io.StringIO(texto)))
    if not filas:
        return []
    cab = filas[0]
    if fuente == "fred":
        i_f, i_v = 0, 1
    else:
        i_f, i_v = cab.index("TIME_PERIOD"), cab.index("OBS_VALUE")
    salida = []
    for f in filas[1:]:
        try:
            fecha = f[i_f]
            if len(fecha) == 7:  # serie mensual AAAA-MM
                fecha += "-01"
            salida.append((dt.date.fromisoformat(fecha), float(f[i_v])))
        except (ValueError, IndexError):
            continue  # días sin dato («.» en FRED)
    return sorted(salida)


def resumen(datos: list[tuple[dt.date, float]], tasa: bool = False) -> dict:
    """Último dato y variaciones: en % para precios e índices; en puntos para tipos y tasas."""
    fu, vu = datos[-1]

    def hace(dias: int) -> float | None:
        objetivo = fu - dt.timedelta(days=dias)
        previos = [v for f, v in datos if f <= objetivo]
        return previos[-1] if previos else None

    def var(ref):
        if ref is None:
            return None
        return round(vu - ref, 3) if tasa else (round((vu / ref - 1) * 100, 2) if ref else None)
    return {"ultimo": vu, "fecha": fu.isoformat(), "variacion_en": "puntos" if tasa else "%",
            "var_anterior": var(datos[-2][1] if len(datos) > 1 else None),
            "var_1m": var(hace(30)), "var_1a": var(hace(365))}


def compacta(datos: list[tuple[dt.date, float]], anios: int = 2) -> str:
    """Cierres semanales (último dato de cada semana) de los últimos años más el último dato,
    en texto compacto «AAAAMMDD:valor;...» para la base de datos de la Hemeroteca."""
    if not datos:
        return ""
    limite = datos[-1][0] - dt.timedelta(days=365 * anios)
    semanas: dict[tuple[int, int], tuple[dt.date, float]] = {}
    for f, v in datos:
        if f >= limite:
            semanas[f.isocalendar()[:2]] = (f, v)
    puntos = sorted(semanas.values())
    if puntos[-1] != datos[-1]:
        puntos.append(datos[-1])
    return ";".join(f"{f:%Y%m%d}:{v:.6g}" for f, v in puntos)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Series de mercado de Pyxis.")
    p.add_argument("config")
    p.add_argument("datos")
    p.add_argument("graficas")
    p.add_argument("--anios", type=int, default=2)
    a = p.parse_args(argv)
    series = json.loads(Path(a.config).read_text(encoding="utf-8"))["series"]
    datos_dir, graf_dir = Path(a.datos), Path(a.graficas)
    datos_dir.mkdir(parents=True, exist_ok=True)
    graf_dir.mkdir(parents=True, exist_ok=True)
    rob = Robots()
    desde = (dt.date.today() - dt.timedelta(days=365 * max(a.anios, 1) + 40)).isoformat()
    estado = {}
    hemeroteca: dict[str, dict] = {}
    for s in series:
        archivo, _, serie_bde = s["codigo"].partition(":")
        url = URLS[s["fuente"]].format(codigo=s["codigo"], desde=desde, archivo=archivo)
        permitido, _ = rob.permite(url)
        if not permitido:
            estado[s["id"]] = {"error": "robots.txt no lo permite"}
            continue
        codigo, _, cuerpo, error = descargar(url, 20_000_000)
        if not cuerpo or error:
            datos = []
        elif s["fuente"] == "bde":
            datos = parsear_bde(cuerpo.decode("latin-1", "replace"), serie_bde)
        else:
            datos = parsear(s["fuente"], cuerpo.decode("utf-8", "replace"))
        if not datos:
            estado[s["id"]] = {"error": error or f"sin datos (HTTP {codigo})"}
            print(f"{s['id']:<14} ERROR {estado[s['id']]['error']}")
            continue
        with open(datos_dir / f"{s['id']}.csv", "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["fecha", "valor"])
            w.writerows((f.isoformat(), v) for f, v in datos)
        limite = datos[-1][0] - dt.timedelta(days=365 * a.anios)
        tramo = [d for d in datos if d[0] >= limite]
        svg = grafica_svg([(s["titulo"], tramo)], s["titulo"], s["unidad"], s.get("pie", ""),
                          s.get("fuente_texto", ""), frecuencia=s.get("frecuencia", "Cierres diarios"))
        (graf_dir / f"{s['id']}.svg").write_text(svg, encoding="utf-8")
        estado[s["id"]] = {"titulo": s["titulo"], "unidad": s["unidad"], **resumen(datos, "%" in s["unidad"])}
        hemeroteca[s["id"]] = {"titulo": s["titulo"], "unidad": s["unidad"], "pie": s.get("pie", ""),
                               "fuente": s.get("fuente_texto", ""), "frecuencia": s.get("frecuencia", "Cierres diarios"),
                               "puntos": compacta(datos, a.anios)}
        print(f"{s['id']:<14} ok  {estado[s['id']]['fecha']}  {estado[s['id']]['ultimo']}")
        time.sleep(1)
    (datos_dir / "hemeroteca.json").write_text(json.dumps(
        {"generado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
         "nota": "Cierres semanales de los dos últimos años y último dato. Formato de puntos: AAAAMMDD:valor;...",
         "series": hemeroteca}, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (datos_dir / "resumen.json").write_text(json.dumps(
        {"generado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "series": estado},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
