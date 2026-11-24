# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Agrupa los titulares del panel por historia y mide qué parte del espectro la cubre.

Método (sin dependencias): cada titular, con el principio de su extracto, se convierte en un
vector TF-IDF de palabras normalizadas (sin tildes ni palabras vacías). Los titulares se
recorren por orden de fecha y cada uno se une a la historia más parecida (coseno con su
centroide) si supera un umbral; si no, abre una historia nueva.

Cobertura de una historia: para cada grupo del panel (izq, centro, dcha), qué proporción de
sus medios la publica. Las tres proporciones se normalizan a 100, así un grupo con más medios
no pesa más. Es una medida de qué medios cubren la historia, no de cómo la cuentan.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter, defaultdict

VACIAS = set("""a al algo algun alguna algunas alguno algunos ante antes aqui asi aun bajo bien cada como con
contra cual cuando de del desde donde dos el ella ellas ellos en entre era es esa esas ese eso esos esta estas
este esto estos fue fueron ha han hasta hay la las le les lo los mas me mi mientras muy nada ni no nos o otra
otras otro otros para pero poco por porque que quien se segun ser si sin sobre son su sus tambien tan te tiene
tienen todo todos tras tu un una unas uno unos y ya ademas hoy ayer manana dice dicen asegura afirma tras sera
seran puede pueden hace hacer va van ante sus nuevo nueva nuevos nuevas mismo misma primer primera ultimo ultima
directo ultima hora video videos foto fotos asi esto claves todo lo que sabemos minuto""".split())


UMBRAL = 0.26      # parecido mínimo (coseno) para unir un titular a una historia
FUSION = 0.45      # parecido mínimo entre dos historias (centroides) para fusionarlas en una segunda pasada
MIN_MEDIOS = 3     # una historia entra en la lista si la cubren al menos estos medios
MAX_HISTORIAS = 40
PUNTO_CIEGO = 70   # % de la cobertura normalizada en un solo lado (igual que la Hemeroteca)


def _normaliza(texto: str) -> list[str]:
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    palabras = re.findall(r"[a-z0-9ñ]+", t)
    return [p[:7] for p in palabras if len(p) > 2 and p not in VACIAS and not p.isdigit()]


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    v = {w: c * idf.get(w, 0.0) for w, c in tf.items()}
    n = math.sqrt(sum(x * x for x in v.values())) or 1.0
    return {w: x / n for w, x in v.items()}


def _coseno(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(w, 0.0) for w, x in a.items())


def agrupar(entradas: list[dict], umbral: float = UMBRAL, fusion: float = FUSION) -> list[dict]:
    """entradas: dicts con titulo, extracto, medio, url, fecha. Devuelve historias."""
    docs = [_normaliza(e["titulo"] + " " + e["titulo"] + " " + (e.get("extracto") or "")[:200]) for e in entradas]
    df = Counter(w for d in docs for w in set(d))
    n = len(docs) or 1
    idf = {w: math.log(1 + n / c) for w, c in df.items()}
    vecs = [_vector(d, idf) for d in docs]
    historias: list[dict] = []
    orden = sorted(range(len(entradas)), key=lambda i: entradas[i].get("fecha") or entradas[i].get("recogido") or "")
    for i in orden:
        mejor, sim = None, 0.0
        for h in historias:
            s = _coseno(vecs[i], h["centro"])
            if s > sim:
                mejor, sim = h, s
        if mejor is not None and sim >= umbral:
            mejor["items"].append(i)
            c = defaultdict(float)
            for j in mejor["items"]:
                for w, x in vecs[j].items():
                    c[w] += x
            norma = math.sqrt(sum(x * x for x in c.values())) or 1.0
            mejor["centro"] = {w: x / norma for w, x in c.items()}
        else:
            historias.append({"items": [i], "centro": dict(vecs[i])})
    # Segunda pasada: une historias partidas (mismo hecho contado con palabras distintas al principio).
    fusionadas = True
    while fusionadas:
        fusionadas = False
        historias.sort(key=lambda h: -len(h["items"]))
        for a in range(len(historias)):
            for b in range(a + 1, len(historias)):
                if _coseno(historias[a]["centro"], historias[b]["centro"]) >= fusion:
                    historias[a]["items"] += historias.pop(b)["items"]
                    c = defaultdict(float)
                    for j in historias[a]["items"]:
                        for w, x in vecs[j].items():
                            c[w] += x
                    norma = math.sqrt(sum(x * x for x in c.values())) or 1.0
                    historias[a]["centro"] = {w: x / norma for w, x in c.items()}
                    fusionadas = True
                    break
            if fusionadas:
                break
    salida = []
    for h in historias:
        items = [entradas[i] for i in h["items"]]
        rep = max(h["items"], key=lambda i: _coseno(vecs[i], h["centro"]))
        salida.append({"entradas": items, "medios": sorted({e["medio"] for e in items}),
                       "titular": entradas[rep]["titulo"],
                       "claves": [w for w, _ in sorted(h["centro"].items(), key=lambda x: -x[1])[:6]]})
    return sorted(salida, key=lambda h: -len(h["medios"]))


def cobertura(medios: list[str], grupos: dict[str, str]) -> dict:
    """Proporción de medios de cada grupo que cubren la historia, normalizada a 100."""
    tam = Counter(grupos.values())
    tiene = Counter(grupos[m] for m in medios if m in grupos)
    tasas = {g: tiene[g] / tam[g] for g in ("izq", "centro", "dcha") if tam[g]}
    total = sum(tasas.values()) or 1.0
    pct = {g: round(100 * tasas.get(g, 0) / total) for g in ("izq", "centro", "dcha")}
    return {**pct, "medios": len([m for m in medios if m in grupos]),
            "por_grupo": {g: f"{tiene[g]}/{tam[g]}" for g in ("izq", "centro", "dcha")}}


def punto_ciego(c: dict) -> str | None:
    """'izq' o 'dcha' si un lado acapara la cobertura; None si no."""
    if c["medios"] < MIN_MEDIOS:
        return None
    for g in ("izq", "dcha"):
        if c[g] >= PUNTO_CIEGO:
            return g
    return None


def lista_historias(entradas: list[dict], grupos: dict[str, str], minimo: int = MIN_MEDIOS,
                    maximo: int = MAX_HISTORIAS, corta=lambda t: t) -> tuple[str, int]:
    """Texto para el puente: una línea por historia cubierta por al menos `minimo` medios.

    «N medios | izq x % · centro y % · dcha z % | (medios por grupo: izq a/9, …) | [PUNTO CIEGO: ...] | titular | medios»
    """
    lineas = []
    for h in agrupar([e for e in entradas if e.get("medio") in grupos]):
        c = cobertura(h["medios"], grupos)
        if c["medios"] < minimo:
            continue
        pg = c["por_grupo"]
        pc = punto_ciego(c)
        aviso = {"izq": "PUNTO CIEGO: casi solo izquierda", "dcha": "PUNTO CIEGO: casi solo derecha"}.get(pc)
        partes = [f"{c['medios']} medios", f"izq {c['izq']} % · centro {c['centro']} % · dcha {c['dcha']} %",
                  f"(medios por grupo: izq {pg['izq']}, centro {pg['centro']}, dcha {pg['dcha']})"] + ([aviso] if aviso else []) + \
                 [corta(h["titular"]), ", ".join(h["medios"])]
        lineas.append(" | ".join(partes))
        if len(lineas) >= maximo:
            break
    return "\n".join(lineas), len(lineas)
