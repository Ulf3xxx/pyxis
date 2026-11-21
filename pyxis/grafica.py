# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Gráficas de mercado en SVG, con el estilo de la sección de Economía y mercados.

Fondo azul noche, línea turquesa de 2 px, rejilla discreta, punto en el último cierre
y pie con la fuente. Sin dependencias: solo la biblioteca estándar.

Uso como módulo:
    svg = grafica_svg(serie, titulo="S&P 500", unidad="Puntos", ...)

Uso desde la línea de órdenes (CSV con columnas fecha,valor):
    python -m pyxis.grafica DATOS.csv SALIDA.svg --titulo "S&P 500" --unidad Puntos \
        --pie "SPX · Índice bursátil" --fuente "FRED (S&P Dow Jones Indices)"
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
from html import escape
from pathlib import Path

# Paleta (contraste comprobado sobre el fondo; texto siempre en tonos de texto, no del color de la serie)
FONDO = "#0e2230"
REJILLA = "#2b4250"
TEXTO = "#f4efe6"
TEXTO_2 = "#a9b8c2"
ACENTO = "#7fd8cf"          # etiqueta superior
UNA_SERIE = "#5fd0c5"       # turquesa claro cuando hay una sola serie
# Varias series: orden fijo, nunca cíclico; validado sobre FONDO (banda de luminosidad,
# separación para daltonismo y contraste) con el validador de paletas de dataviz.
SERIES = ["#1ea999", "#d95926", "#3987e5", "#d55181"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_MAY = [m.upper() for m in MESES]

ANCHO, ALTO = 860, 650
M_IZQ, M_DER = 92, 46
Y_ARRIBA, Y_ABAJO = 250, 525


def _paso_bonito(rango: float, divisiones: int = 6) -> float:
    bruto = rango / max(divisiones, 1)
    exp = 10 ** math.floor(math.log10(bruto)) if bruto > 0 else 1
    for f in (1, 2, 2.5, 5, 10):
        if bruto <= f * exp:
            return f * exp
    return 10 * exp


def _num(v: float, decimales: int) -> str:
    texto = f"{v:,.{decimales}f}"
    return texto.replace(",", " ").replace(".", ",") if decimales else texto.replace(",", ".")


def grafica_svg(series: list[tuple[str, list[tuple[dt.date, float]]]], titulo: str, unidad: str,
                pie: str = "", fuente: str = "", etiqueta: str = "MERCADOS",
                frecuencia: str = "Cierres diarios") -> str:
    """series: [(nombre, [(fecha, valor), ...]), ...] — una o varias, con la misma unidad."""
    puntos = [p for _, s in series for p in s]
    if not puntos:
        raise ValueError("serie vacía")
    f0 = min(p[0] for p in puntos)
    f1 = max(p[0] for p in puntos)
    vmin = min(p[1] for p in puntos)
    vmax = max(p[1] for p in puntos)
    holgura = (vmax - vmin) * 0.04 or abs(vmax) * 0.02 or 1
    paso = _paso_bonito(vmax - vmin + 2 * holgura)
    y0 = math.floor((vmin - holgura) / paso) * paso
    y1 = math.ceil((vmax + holgura) / paso) * paso
    if y1 == y0:
        y1 = y0 + paso
    decimales = 0
    while decimales < 4 and abs(paso * 10 ** decimales - round(paso * 10 ** decimales)) > 1e-9:
        decimales += 1
    dias = max((f1 - f0).days, 1)

    def X(f: dt.date) -> float:
        return M_IZQ + (f - f0).days / dias * (ANCHO - M_IZQ - M_DER)

    def Y(v: float) -> float:
        return Y_ABAJO - (v - y0) / (y1 - y0) * (Y_ABAJO - Y_ARRIBA)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ANCHO} {ALTO}" role="img" '
         f'aria-label="{escape(titulo)}: {escape(unidad)}, {f0:%d/%m/%Y} a {f1:%d/%m/%Y}" '
         f'font-family="\'IBM Plex Sans\', \'Inter\', system-ui, sans-serif">']
    o.append(f'<rect width="{ANCHO}" height="{ALTO}" rx="6" fill="{FONDO}"/>')
    periodo = f"{MESES_MAY[f0.month - 1]} {f0.year} — {MESES_MAY[f1.month - 1]} {f1.year}"
    o.append(f'<text x="48" y="56" font-size="18" letter-spacing="1.5" fill="{ACENTO}">{escape(etiqueta)}'
             f'<tspan dx="18" fill="{TEXTO_2}">/</tspan><tspan dx="18">{periodo}</tspan></text>')
    o.append(f'<text x="44" y="124" font-size="52" font-weight="800" fill="{TEXTO}" '
             f'font-family="\'Archivo Black\', \'Arial Black\', sans-serif">{escape(titulo)}</text>')
    o.append(f'<text x="48" y="178" font-size="20" fill="{TEXTO_2}">{escape(unidad)}'
             f'<tspan dx="12">·</tspan><tspan dx="12">{escape(frecuencia)}</tspan></text>')
    # Leyenda solo con dos o más series (con una, el título la nombra)
    if len(series) > len(SERIES):
        raise ValueError(f"como mucho {len(SERIES)} series por gráfica")
    if len(series) > 1:
        x = 48
        for i, (nombre, _) in enumerate(series):
            o.append(f'<rect x="{x}" y="204" width="34" height="5" rx="2.5" fill="{SERIES[i]}"/>')
            o.append(f'<text x="{x + 46}" y="212" font-size="19" fill="{TEXTO}">{escape(nombre)}</text>')
            x += 46 + 11 * len(nombre) + 36
    # Rejilla y eje Y
    v = y0
    while v <= y1 + paso / 2:
        y = Y(v)
        o.append(f'<line x1="{M_IZQ}" x2="{ANCHO - M_DER}" y1="{y:.1f}" y2="{y:.1f}" stroke="{REJILLA}" stroke-width="1"/>')
        o.append(f'<text x="{M_IZQ - 12}" y="{y + 6:.1f}" font-size="16" fill="{TEXTO_2}" text-anchor="end">{_num(v, decimales)}</text>')
        v += paso
    # Eje X: 5 marcas repartidas, etiquetadas por mes y año
    for i in range(5):
        f = f0 + dt.timedelta(days=round(dias * i / 4))
        x = X(f)
        anchor = "start" if i == 0 else "end" if i == 4 else "middle"
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y_ABAJO}" y2="{Y_ABAJO + 6}" stroke="{TEXTO_2}" stroke-width="1"/>')
        o.append(f'<text x="{x:.1f}" y="{Y_ABAJO + 30}" font-size="17" fill="{TEXTO_2}" text-anchor="{anchor}">'
                 f'{MESES[f.month - 1].capitalize()} {f.year % 100:02d}</text>')
    # Series
    for i, (_, s) in enumerate(series):
        color = UNA_SERIE if len(series) == 1 else SERIES[i % len(SERIES)]
        s = sorted(s)
        d = " ".join(f"{'M' if j == 0 else 'L'}{X(f):.1f},{Y(val):.1f}" for j, (f, val) in enumerate(s))
        o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        fu, vu = s[-1]
        o.append(f'<circle cx="{X(fu):.1f}" cy="{Y(vu):.1f}" r="6" fill="{color}" stroke="{FONDO}" stroke-width="2"/>')
    if pie:
        o.append(f'<text x="48" y="{ALTO - 58}" font-size="23" fill="{TEXTO}">{escape(pie)}</text>')
    mensual = "mensual" in frecuencia.lower()
    hasta = f"{MESES[f1.month - 1]} {f1.year}" if mensual else f"el {f1.day} {MESES[f1.month - 1]} {f1.year}"
    nota = f"Fuente: {fuente} · Datos hasta {hasta}" if fuente else ""
    if nota:
        o.append(f'<text x="48" y="{ALTO - 20}" font-size="15" fill="{TEXTO_2}">{escape(nota)}</text>')
    o.append("</svg>")
    return "\n".join(o)


def leer_csv(ruta: Path) -> list[tuple[dt.date, float]]:
    salida = []
    with open(ruta, encoding="utf-8") as fh:
        for fila in csv.reader(fh):
            try:
                salida.append((dt.date.fromisoformat(fila[0]), float(fila[1])))
            except (ValueError, IndexError):
                continue  # cabecera o día sin dato
    return salida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gráfica de mercado en SVG.")
    p.add_argument("csv", nargs="+", help="uno o varios CSV fecha,valor (nombre=ruta para dar nombre a la serie)")
    p.add_argument("salida")
    p.add_argument("--titulo", required=True)
    p.add_argument("--unidad", required=True)
    p.add_argument("--pie", default="")
    p.add_argument("--fuente", default="")
    p.add_argument("--desde", help="AAAA-MM-DD")
    a = p.parse_args(argv)
    series = []
    for item in a.csv:
        nombre, _, ruta = item.rpartition("=")
        datos = leer_csv(Path(ruta))
        if a.desde:
            datos = [d for d in datos if d[0] >= dt.date.fromisoformat(a.desde)]
        series.append((nombre or a.titulo, datos))
    Path(a.salida).write_text(grafica_svg(series, a.titulo, a.unidad, a.pie, a.fuente), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
