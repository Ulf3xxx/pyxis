# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sonda de GDELT: comprueba qué medios de un panel aparecen en GDELT.

GDELT (https://www.gdeltproject.org) indexa titulares y enlaces de prensa de
todo el mundo y los ofrece por una API pública sin clave. Esta sonda pregunta,
medio por medio, cuántos artículos recientes conoce GDELT de cada dominio.
Solo lee metadatos (título, enlace, fecha): no abre ni descarga los artículos.

Uso:
    python -m pyxis.sonda_gdelt PANEL.json SALIDA.json [--horas 24]

PANEL.json debe tener la forma {"medios": [{"nombre": ..., "dominio": ..., "grupo": ...}]}.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.gdeltproject.org/api/v2/doc/doc"
PAUSA = 6.0  # GDELT pide no superar una consulta cada 5 segundos
AGENTE = "pyxis-sonda/0.0.1 (+https://github.com/Ulf3xxx/pyxis)"


def consultar(dominio: str, horas: int, maximo: int = 75) -> dict:
    """Devuelve {"ok", "articulos", "error"} para un dominio."""
    parametros = {
        "query": f"domainis:{dominio}",
        "mode": "artlist",
        "maxrecords": str(maximo),
        "timespan": f"{horas}h",
        "sort": "datedesc",
        "format": "json",
    }
    url = API + "?" + urllib.parse.urlencode(parametros)
    peticion = urllib.request.Request(url, headers={"User-Agent": AGENTE})
    for intento in range(3):
        try:
            with urllib.request.urlopen(peticion, timeout=40) as r:
                cuerpo = r.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            error = f"red: {e}"
        else:
            try:
                datos = json.loads(cuerpo) if cuerpo.strip() else {}
            except json.JSONDecodeError:
                # GDELT responde con texto plano cuando rechaza o limita la consulta
                error = "respuesta no JSON: " + cuerpo.strip()[:160]
            else:
                return {"ok": True, "articulos": datos.get("articles", []), "error": None}
        time.sleep(PAUSA * (intento + 2))
    return {"ok": False, "articulos": [], "error": error}


def sondear(medios: list[dict], horas: int) -> dict:
    resultados = []
    for i, m in enumerate(medios):
        if i:
            time.sleep(PAUSA)
        r = consultar(m["dominio"], horas)
        arts = r["articulos"]
        resultados.append(
            {
                "nombre": m["nombre"],
                "dominio": m["dominio"],
                "grupo": m.get("grupo"),
                "consulta_ok": r["ok"],
                "error": r["error"],
                "articulos": len(arts),
                "tope_alcanzado": len(arts) >= 75,
                "idiomas": sorted({a.get("language", "") for a in arts} - {""}),
                "mas_reciente": max((a.get("seendate", "") for a in arts), default=None),
                "muestra": [{"titulo": a.get("title"), "url": a.get("url"), "visto": a.get("seendate")} for a in arts[:5]],
            }
        )
        print(f"{m['nombre']:<20} {m['dominio']:<22} {'ok' if r['ok'] else 'ERROR':<6} {len(arts):>3} artículos", flush=True)
    por_grupo: dict[str, dict] = {}
    for r in resultados:
        g = por_grupo.setdefault(r["grupo"] or "sin_grupo", {"medios": 0, "con_articulos": 0, "articulos": 0})
        g["medios"] += 1
        g["con_articulos"] += 1 if r["articulos"] else 0
        g["articulos"] += r["articulos"]
    return {
        "fuente": "GDELT DOC 2.0 API",
        "generado": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ventana_horas": horas,
        "nota": "Cuenta de artículos que GDELT conoce por dominio; el tope por consulta es 75.",
        "resumen": {
            "medios": len(resultados),
            "con_articulos": sum(1 for r in resultados if r["articulos"]),
            "consultas_fallidas": sum(1 for r in resultados if not r["consulta_ok"]),
            "por_grupo": por_grupo,
        },
        "medios": resultados,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sonda de cobertura de un panel de medios en GDELT.")
    p.add_argument("panel")
    p.add_argument("salida")
    p.add_argument("--horas", type=int, default=24)
    a = p.parse_args(argv)
    medios = json.loads(Path(a.panel).read_text(encoding="utf-8"))["medios"]
    informe = sondear(medios, a.horas)
    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    r = informe["resumen"]
    print(f"\n{r['con_articulos']} de {r['medios']} medios con artículos; {r['consultas_fallidas']} consultas fallidas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
