# Pyxis — brújula de actualidad
# Copyright (C) 2026 Ulf3xxx y colaboradores de Pyxis
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Valida ediciones de Pyxis contra el esquema de datos (docs/esquema.md).

Uso:
    python -m pyxis.validar RUTA [RUTA ...]

Cada RUTA puede ser un archivo .json o una carpeta (se recorren sus .json).
Devuelve código 0 si no hay errores y 1 si hay alguno. Los avisos no hacen
fallar la validación: señalan cosas que conviene revisar.

Solo usa la biblioteca estándar de Python.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

EDICIONES = {"manana", "mediodia", "noche", "prueba"}
SECCIONES = ["geo", "espana", "internacional", "economia", "tecnologia"]
ESTADOS = {"leida", "buscador", "no_accesible", "sin_novedades"}
RE_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_HORA = re.compile(r"^\d{2}:\d{2}$")


class Informe:
    """Acumula errores y avisos de un documento."""

    def __init__(self) -> None:
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def error(self, donde: str, texto: str) -> None:
        self.errores.append(f"{donde}: {texto}")

    def aviso(self, donde: str, texto: str) -> None:
        self.avisos.append(f"{donde}: {texto}")


def _texto(inf: Informe, obj: dict, campo: str, donde: str, obligatorio: bool = True) -> None:
    valor = obj.get(campo)
    if valor is None:
        if obligatorio:
            inf.error(donde, f"falta «{campo}»")
        return
    if not isinstance(valor, str) or not valor.strip():
        inf.error(donde, f"«{campo}» debe ser un texto no vacío")


def _lista_textos(inf: Informe, obj: dict, campo: str, donde: str, obligatorio: bool = True) -> None:
    valor = obj.get(campo)
    if valor is None:
        if obligatorio:
            inf.error(donde, f"falta «{campo}»")
        return
    if not isinstance(valor, list) or not all(isinstance(x, str) for x in valor):
        inf.error(donde, f"«{campo}» debe ser una lista de textos")


def _url(inf: Informe, valor: object, donde: str) -> None:
    if not isinstance(valor, str) or not valor.startswith(("http://", "https://")):
        inf.error(donde, "la URL debe empezar por http:// o https://")


def _noticia(inf: Informe, n: object, donde: str) -> None:
    if not isinstance(n, dict):
        inf.error(donde, "la noticia debe ser un objeto")
        return
    for campo in ("titular", "texto", "porque"):
        _texto(inf, n, campo, donde)
    _texto(inf, n, "como_lo_cuentan", donde, obligatorio=False)
    if "actualizacion" in n and not isinstance(n["actualizacion"], bool):
        inf.error(donde, "«actualizacion» debe ser true o false")
    fuentes = n.get("fuentes")
    if not isinstance(fuentes, list) or not fuentes:
        inf.error(donde, "cada noticia necesita al menos una fuente")
        return
    for i, f in enumerate(fuentes):
        d = f"{donde}.fuentes[{i}]"
        if not isinstance(f, dict):
            inf.error(d, "la fuente debe ser un objeto")
            continue
        _texto(inf, f, "nombre", d)
        _url(inf, f.get("url"), d)


def _contenido(inf: Informe, c: object) -> list[str]:
    """Valida «contenido» y devuelve los titulares que contiene."""
    titulares: list[str] = []
    if not isinstance(c, dict):
        inf.error("contenido", "debe ser un objeto")
        return titulares
    _lista_textos(inf, c, "esencial", "contenido")
    secciones = c.get("secciones")
    if not isinstance(secciones, list):
        inf.error("contenido", "falta la lista «secciones»")
        secciones = []
    vistos: list[str] = []
    for i, s in enumerate(secciones):
        d = f"contenido.secciones[{i}]"
        if not isinstance(s, dict):
            inf.error(d, "la sección debe ser un objeto")
            continue
        sid = s.get("id")
        if sid not in SECCIONES:
            inf.error(d, f"«id» desconocido: {sid!r}")
        else:
            vistos.append(sid)
        _texto(inf, s, "nombre", d)
        if s.get("nota") is not None and not isinstance(s.get("nota"), str):
            inf.error(d, "«nota» debe ser un texto")
        noticias = s.get("noticias")
        if not isinstance(noticias, list):
            inf.error(d, "falta la lista «noticias»")
            continue
        if not noticias and not s.get("nota"):
            inf.aviso(d, "sección vacía sin «nota» que lo explique")
        for j, n in enumerate(noticias):
            _noticia(inf, n, f"{d}.noticias[{j}]")
            if isinstance(n, dict) and isinstance(n.get("titular"), str):
                titulares.append(n["titular"])
    if vistos != [s for s in SECCIONES if s in vistos]:
        inf.aviso("contenido.secciones", "las secciones no siguen el orden geo, espana, internacional, economia, tecnologia")
    for campo, claves in (
        ("lecturas", ("fuente", "titulo", "url", "resumen")),
        ("videos", ("canal", "titulo", "url", "descripcion")),
    ):
        for i, x in enumerate(c.get(campo) or []):
            d = f"contenido.{campo}[{i}]"
            if not isinstance(x, dict):
                inf.error(d, "debe ser un objeto")
                continue
            for k in claves:
                if k == "url":
                    _url(inf, x.get("url"), d)
                else:
                    _texto(inf, x, k, d)
    for i, r in enumerate(c.get("revision") or []):
        d = f"contenido.revision[{i}]"
        if not isinstance(r, dict):
            inf.error(d, "debe ser un objeto")
            continue
        _texto(inf, r, "fuente", d)
        if r.get("estado") not in ESTADOS:
            inf.error(d, f"«estado» desconocido: {r.get('estado')!r}")
    if c.get("notas") is not None and not isinstance(c.get("notas"), str):
        inf.error("contenido", "«notas» debe ser un texto")
    return titulares


def validar_edicion(doc: object) -> Informe:
    """Valida un documento de edición ya cargado y devuelve su informe."""
    inf = Informe()
    if not isinstance(doc, dict):
        inf.error("documento", "debe ser un objeto JSON")
        return inf
    fecha = doc.get("fecha")
    if not isinstance(fecha, str) or not RE_FECHA.match(fecha):
        inf.error("fecha", "debe tener el formato AAAA-MM-DD")
    if doc.get("edicion") not in EDICIONES:
        inf.error("edicion", f"debe ser una de {sorted(EDICIONES)}")
    hora = doc.get("hora")
    if not isinstance(hora, str) or not RE_HORA.match(hora):
        inf.error("hora", "debe tener el formato HH:MM")
    _texto(inf, doc, "titulo", "documento")
    _texto(inf, doc, "resumen", "documento")
    _lista_textos(inf, doc, "destacados", "documento")
    _lista_textos(inf, doc, "temas", "documento")

    indice: list[str] = []
    if "noticias" in doc:
        if not isinstance(doc["noticias"], list):
            inf.error("noticias", "debe ser una lista")
        else:
            for i, n in enumerate(doc["noticias"]):
                d = f"noticias[{i}]"
                if not isinstance(n, dict):
                    inf.error(d, "debe ser un objeto")
                    continue
                _texto(inf, n, "seccion", d)
                _texto(inf, n, "titular", d)
                if isinstance(n.get("titular"), str):
                    indice.append(n["titular"])

    if "contenido" in doc:
        titulares = _contenido(inf, doc["contenido"])
        if "noticias" in doc and sorted(indice) != sorted(titulares):
            solo_indice = sorted(set(indice) - set(titulares))
            solo_contenido = sorted(set(titulares) - set(indice))
            inf.aviso(
                "noticias",
                f"el índice ({len(indice)}) y el contenido ({len(titulares)}) no coinciden; "
                f"solo en el índice: {solo_indice}; solo en el contenido: {solo_contenido}",
            )
    elif "url" in doc:
        _url(inf, doc["url"], "url")
        inf.aviso("documento", "edición antigua: sin «contenido», solo índice y enlace")
    else:
        inf.error("documento", "falta «contenido» (o «url» en ediciones antiguas)")
    return inf


def _archivos(rutas: list[str]) -> list[Path]:
    salida: list[Path] = []
    for r in rutas:
        p = Path(r)
        if p.is_dir():
            salida.extend(sorted(p.rglob("*.json")))
        else:
            salida.append(p)
    return salida


def main(argv: list[str] | None = None) -> int:
    rutas = list(sys.argv[1:] if argv is None else argv)
    if not rutas:
        print(__doc__)
        return 2
    total_errores = 0
    archivos = _archivos(rutas)
    for archivo in archivos:
        try:
            doc = json.loads(archivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"✗ {archivo}: no se pudo leer como JSON ({e})")
            total_errores += 1
            continue
        inf = validar_edicion(doc)
        marca = "✗" if inf.errores else "✓"
        print(f"{marca} {archivo}  ({len(inf.errores)} errores, {len(inf.avisos)} avisos)")
        for e in inf.errores:
            print(f"    error  {e}")
        for a in inf.avisos:
            print(f"    aviso  {a}")
        total_errores += len(inf.errores)
    print(f"\n{len(archivos)} archivos revisados, {total_errores} errores.")
    return 1 if total_errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
