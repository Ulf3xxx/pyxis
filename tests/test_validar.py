# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del validador. Ejecutar con: python -m unittest discover -s tests"""
import copy
import json
import unittest
from pathlib import Path

from pyxis.validar import validar_edicion

EJEMPLO = json.loads(
    (Path(__file__).parent.parent / "ejemplos" / "edicion-ejemplo.json").read_text(encoding="utf-8")
)


class ValidarEdicion(unittest.TestCase):
    def test_ejemplo_valido(self):
        inf = validar_edicion(EJEMPLO)
        self.assertEqual(inf.errores, [])
        self.assertEqual(inf.avisos, [])

    def test_fecha_mal_formada(self):
        doc = copy.deepcopy(EJEMPLO)
        doc["fecha"] = "15/01/2030"
        self.assertTrue(any("fecha" in e for e in validar_edicion(doc).errores))

    def test_noticia_sin_fuentes(self):
        doc = copy.deepcopy(EJEMPLO)
        doc["contenido"]["secciones"][3]["noticias"][0]["fuentes"] = []
        self.assertTrue(any("fuente" in e for e in validar_edicion(doc).errores))

    def test_estado_de_revision_desconocido(self):
        doc = copy.deepcopy(EJEMPLO)
        doc["contenido"]["revision"][0]["estado"] = "quizas"
        self.assertTrue(any("estado" in e for e in validar_edicion(doc).errores))

    def test_indice_y_contenido_distintos_es_aviso(self):
        doc = copy.deepcopy(EJEMPLO)
        doc["noticias"].append({"seccion": "España", "titular": "Titular que no está en el contenido"})
        inf = validar_edicion(doc)
        self.assertEqual(inf.errores, [])
        self.assertTrue(any("no coinciden" in a for a in inf.avisos))

    def test_edicion_por_actualizacion(self):
        doc = copy.deepcopy(EJEMPLO)
        doc["base"] = "2030-01-15-manana"
        doc["contenido"]["secciones"][3]["noticias"][0]["estado"] = "actualizada"
        self.assertEqual(validar_edicion(doc).errores, [])
        doc["contenido"]["secciones"][3]["noticias"][0]["estado"] = "otra"
        self.assertTrue(any("estado" in e for e in validar_edicion(doc).errores))

    def test_videos_en_noticias_y_secciones(self):
        doc = copy.deepcopy(EJEMPLO)
        sec = doc["contenido"]["secciones"][3]
        v = {"canal": "Solo Fonseca", "titulo": "Batalla en el inframundo", "url": "https://www.youtube.com/watch?v=x",
             "fecha": "2026-11-20", "trata": "El avance ucraniano por un gasoducto.",
             "postura": "Lo presenta como un éxito ucraniano."}
        sec["noticias"][0]["videos"] = [v]
        sec["videos"] = [dict(v, tema="Guerra de Ucrania")]
        self.assertEqual(validar_edicion(doc).errores, [])
        sec["videos"] = [{"canal": "X", "titulo": "Y", "url": "ftp://z"}]
        self.assertTrue(any("videos" in e for e in validar_edicion(doc).errores))

    def test_edicion_antigua_con_url(self):
        doc = {k: v for k, v in EJEMPLO.items() if k != "contenido"}
        doc["url"] = "https://example.org/edicion"
        self.assertEqual(validar_edicion(doc).errores, [])


if __name__ == "__main__":
    unittest.main()

