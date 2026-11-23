# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Indicadores oficiales para especiales (por ejemplo, unas elecciones).

Convierte los datos de Eurostat (API JSON-stat, ya descargados en un informe JSON con
{"indicadores": {clave: {"datos": {"ES": {periodo: valor}, "EU27_2020": {...}}}}}) en
series para la Hemeroteca: puntos «AAAAMMDD:valor;...» para España y, como comparación,
para la UE-27, y una tabla con el valor de un año de referencia y el último disponible.

Uso:
    python -m pyxis.indicadores CONFIG.json INFORME.json [INFORME2.json ...] --salida SALIDA.json

CONFIG.json: {"referencia": "2018", "series": [{"id": "paro", "clave": "paro",
  "titulo": "Paro", "unidad": "% de la población activa", "frecuencia": "Anual",
  "fuente": "Eurostat (une_rt_a)", "pie": "...", "serie_es": "ES", "serie_ue": "EU27_2020",
  "desde": "2015", "decimales": 1}]}
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def fecha(periodo: str) -> str:
    """'2025' -> 20250701; '2026-03' -> 20260315; '2026-Q2' -> 20260515; '2026-S1' -> 20260401."""
    p = periodo.strip()
    if re.fullmatch(r"\d{4}", p):
        return p + "0701"
    m = re.fullmatch(r"(\d{4})-(\d{2})", p)
    if m:
        return m.group(1) + m.group(2) + "15"
    m = re.fullmatch(r"(\d{4})-Q([1-4])", p)
    if m:
        return m.group(1) + f"{3 * int(m.group(2)) - 1:02d}15"
    m = re.fullmatch(r"(\d{4})-S([12])", p)
    if m:
        return m.group(1) + ("0401" if m.group(2) == "1" else "1001")
    raise ValueError(f"periodo no reconocido: {periodo}")


def puntos(serie: dict[str, float], desde: str = "") -> str:
    return ";".join(f"{fecha(p)}:{v:g}" for p, v in sorted(serie.items()) if p >= desde and v is not None)


def construir(config: dict, informes: list[dict]) -> dict:
    datos = {}
    for inf in informes:
        for k, v in inf.get("indicadores", {}).items():
            if v.get("datos"):
                datos[k] = v  # los informes posteriores corrigen a los anteriores
    ref = config.get("referencia", "2018")
    series, tabla = {}, []
    for s in config["series"]:
        ind = datos.get(s["clave"])
        if not ind:
            continue
        es = dict(ind["datos"].get(s.get("serie_es", "ES"), {}))
        for extra in s.get("unir", []):  # otra clave que continúa la serie (p. ej. cambio de clasificación)
            otro = datos.get(extra["clave"], {}).get("datos", {}).get(extra.get("serie_es", "ES"), {})
            es.update({p: v for p, v in otro.items() if p >= extra.get("desde", "")})
        ue = dict(ind["datos"].get(s.get("serie_ue", "EU27_2020"), {})) if s.get("serie_ue", "EU27_2020") else {}
        for extra in s.get("unir", []):
            if s.get("serie_ue", "EU27_2020"):
                otro = datos.get(extra["clave"], {}).get("datos", {}).get(extra.get("serie_ue", "EU27_2020"), {})
                ue.update({p: v for p, v in otro.items() if p >= extra.get("desde", "")})
        if not es:
            continue
        desde = s.get("desde", "2015")
        reg = {k: s[k] for k in ("titulo", "unidad", "frecuencia", "fuente", "pie") if k in s}
        reg["puntos"] = puntos(es, desde)
        if ue:
            reg["comparar"] = puntos(ue, desde)
            reg["comparar_nombre"] = "UE-27"
        series[s["id"]] = reg
        ultimo = max(es)
        ref_p = ref if ref in es else next((p for p in sorted(es) if p.startswith(ref)), None)
        tabla.append({"id": s["id"], "indicador": s["titulo"], "unidad": s.get("unidad", ""),
                      "referencia": ref_p, "valor_referencia": es.get(ref_p) if ref_p else None,
                      "ultimo_periodo": ultimo, "ultimo": es[ultimo],
                      "ue_ultimo": ue.get(ultimo) if ue else None, "fuente": s.get("fuente", "")})
    return {"series": series, "tabla": tabla}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config")
    ap.add_argument("informes", nargs="+")
    ap.add_argument("--salida", required=True)
    a = ap.parse_args()
    config = json.loads(Path(a.config).read_text(encoding="utf-8"))
    informes = [json.loads(Path(f).read_text(encoding="utf-8")) for f in a.informes]
    res = construir(config, informes)
    Path(a.salida).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(res['series'])} series; tabla de {len(res['tabla'])} filas")


if __name__ == "__main__":
    main()
