# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del recolector (sin red)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pyxis import recolector

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>
<item><title>Titular &amp; uno</title><link>https://www.ejemplo.es/a/1</link>
<pubDate>Wed, 18 Nov 2026 10:00:00 +0000</pubDate><description>&lt;p&gt;Extracto del primero&lt;/p&gt;</description></item>
<item><title>Titular dos</title><link>https://ejemplo.es/a/2/</link>
<pubDate>Wed, 18 Nov 2026 23:30:00 +0000</pubDate></item>
</channel></rss>"""

ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title>
<link rel="alternate" href="https://ejemplo.org/atom"/><updated>2026-11-18T09:00:00Z</updated>
<summary>Resumen</summary></entry></feed>"""

BLUESKY = {
    "feed": [
        {"post": {"record": {"text": "Noticia https://medio.com/n1", "createdAt": "2026-11-18T08:00:00Z",
                             "embed": {"external": {"uri": "https://medio.com/n1", "title": "Titular bsky",
                                                    "description": "Desc"}}}}},
        {"post": {"record": {"text": "Sin enlace", "createdAt": "2026-11-18T08:00:00Z"}}},
        {"reason": {"$type": "repost"}, "post": {"record": {"text": "https://otro.com/x"}}},
    ]
}


class Analisis(unittest.TestCase):
    def test_rss(self):
        e = recolector.entradas_feed(RSS)
        self.assertEqual(len(e), 2)
        self.assertEqual(e[0]["titulo"], "Titular & uno")
        self.assertEqual(e[0]["extracto"], "Extracto del primero")
        self.assertEqual(e[0]["fecha"], "2026-11-18T10:00:00Z")

    def test_atom(self):
        e = recolector.entradas_feed(ATOM)
        self.assertEqual(e[0]["url"], "https://ejemplo.org/atom")

    def test_no_feed(self):
        self.assertIsNone(recolector.entradas_feed(b"<html></html>"))

    def test_bluesky_solo_propias_con_enlace(self):
        e = recolector.entradas_bluesky(BLUESKY)
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0]["titulo"], "Titular bsky")

    def test_extracto_limitado(self):
        self.assertLessEqual(len(recolector._texto_plano("palabra " * 200)), recolector.MAX_EXTRACTO)

    def test_clave_ignora_www_y_barra_final(self):
        self.assertEqual(recolector._clave("https://www.ejemplo.es/a/2/"), recolector._clave("https://ejemplo.es/a/2"))


class Recoleccion(unittest.TestCase):
    def test_no_repite_entre_ejecuciones_y_separa_por_dia_de_madrid(self):
        fuentes = [{"id": "ej", "nombre": "Ejemplo", "tipo": "rss", "url": "https://ejemplo.es/rss"}]
        ahora = recolector.dt.datetime(2026, 11, 19, 1, 0, tzinfo=recolector.dt.timezone.utc)
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(recolector, "leer_fuente", return_value=(recolector.entradas_feed(RSS), None)), \
                mock.patch.object(recolector, "PAUSA", 0), \
                mock.patch.object(recolector.dt, "datetime", wraps=recolector.dt.datetime) as fdt:
            fdt.now.return_value = ahora
            r1 = recolector.recolectar(fuentes, Path(d))
            r2 = recolector.recolectar(fuentes, Path(d))
            self.assertEqual(r1["entradas_nuevas"], 2)
            self.assertEqual(r2["entradas_nuevas"], 0)
            dia18 = Path(d, "2026", "11", "2026-11-18.jsonl").read_text(encoding="utf-8").splitlines()
            dia19 = Path(d, "2026", "11", "2026-11-19.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(dia18), 1)  # 10:00 UTC
            self.assertEqual(len(dia19), 1)  # 23:30 UTC = 00:30 en Madrid
            self.assertEqual(json.loads(dia18[0])["medio"], "Ejemplo")


if __name__ == "__main__":
    unittest.main()


def test_feed_de_youtube():
    from pyxis.recolector import entradas_feed
    atom = b"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
 <entry>
  <yt:videoId>abc</yt:videoId>
  <title>Por que Groenlandia importa</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=abc"/>
  <published>2026-11-18T10:00:00+00:00</published>
  <media:group><media:title>Por que Groenlandia importa</media:title>
   <media:description>Analisis del Artico y las bases.</media:description></media:group>
 </entry>
</feed>"""
    e = entradas_feed(atom)
    assert e == [{"titulo": "Por que Groenlandia importa", "url": "https://www.youtube.com/watch?v=abc",
                  "fecha": "2026-11-18T10:00:00Z", "extracto": "Analisis del Artico y las bases."}]


def test_canal_en_pagina():
    from pyxis.sonda_youtube import canal_en_pagina
    html = '<link rel="alternate" type="application/rss+xml" href="https://www.youtube.com/feeds/videos.xml?channel_id=UC1234567890abcdefghijkl">'
    assert canal_en_pagina(html) == "UC1234567890abcdefghijkl"


def test_entradas_youtube_y_purga(tmp_path):
    import datetime as dt
    from pyxis.recolector import entradas_youtube, purgar_video
    datos = {"items": [{"snippet": {"title": "Groenlandia", "description": "El Ártico",
             "publishedAt": "2026-11-18T10:00:00Z", "resourceId": {"videoId": "abc"}}}]}
    assert entradas_youtube(datos) == [{"titulo": "Groenlandia", "url": "https://www.youtube.com/watch?v=abc",
                                        "fecha": "2026-11-18T10:00:00Z", "extracto": "El Ártico"}]
    viejo = tmp_path / "2026" / "09" / "2026-09-01.jsonl"
    nuevo = tmp_path / "2026" / "11" / "2026-11-18.jsonl"
    for a in (viejo, nuevo):
        a.parent.mkdir(parents=True, exist_ok=True)
        a.write_text("")
    assert purgar_video(tmp_path, dt.datetime(2026, 11, 19, tzinfo=dt.timezone.utc)) == 1
    assert not viejo.exists() and nuevo.exists()


def test_youtube_sin_clave(monkeypatch):
    from pyxis.recolector import leer_youtube
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    assert leer_youtube({"canal": "UC" + "x" * 22}) == ([], "sin clave YOUTUBE_API_KEY")


def test_clave_distingue_videos():
    from pyxis.recolector import _clave
    assert _clave("https://www.youtube.com/watch?v=a") != _clave("https://www.youtube.com/watch?v=b")
    assert _clave("https://elpais.com/x/?utm=1") == _clave("https://elpais.com/x")


def test_puente_listas(tmp_path):
    import datetime as dt, json
    from pyxis import puente
    d = tmp_path / "recoleccion" / "2026" / "11"
    d.mkdir(parents=True)
    filas = [
        {"medio": "A", "lista": "panel", "titulo": "Uno", "url": "https://a/1", "fecha": "2026-11-19T08:00:00Z"},
        {"medio": "A", "lista": "panel", "titulo": "Viejo", "url": "https://a/0", "fecha": "2026-11-19T06:00:00Z"},
        {"medio": "B", "lista": "analisis", "titulo": "Ensayo", "url": "https://b/1", "fecha": "2026-11-15T10:00:00Z"},
    ]
    (d / "2026-11-19.jsonl").write_text("\n".join(json.dumps(f) for f in filas))
    puente.leer_video = lambda datos, dias: ([], None)
    doc = puente.preparar("mediodia", tmp_path, dt.datetime(2026, 11, 19, 11, 0, tzinfo=dt.timezone.utc))
    assert doc["listas"]["panel"] == "09:00 | A | Uno | https://a/1"  # 06:00Z = 07:00 Madrid, fuera de ventana
    assert doc["cuentas"] == {"panel": 1, "extranjero": 0, "economia": 0, "analisis": 1, "video": 0}


def test_entradas_portada():
    from pyxis.recolector import entradas_portada
    html = b"""<html><body><h2><a href="/espana/2026/11/20/noticia-larga-de-prueba/0003.htm">Un titular suficientemente largo para entrar</a></h2>
    <h3><a href="https://otro.com/x">Un titular de otro dominio que no debe entrar</a></h3>
    <h2><a href="/corto">Corto</a></h2><p><a href="/fuera">Enlace fuera de encabezado con texto largo</a></p></body></html>"""
    e = entradas_portada(html, "https://www.lavozdegalicia.es/")
    assert e == [{"titulo": "Un titular suficientemente largo para entrar",
                  "url": "https://www.lavozdegalicia.es/espana/2026/11/20/noticia-larga-de-prueba/0003.htm",
                  "fecha": None, "extracto": ""}]


def test_portada_enlace_que_contiene_encabezado_y_latin1():
    from pyxis.recolector import entradas_portada
    html = '<meta charset="iso-8859-1"><a href="/galicia/2026/11/20/xunta-aprueba/0003_1.htm"><h2>La Xunta aprueba los presupuestos de 2027 con cambios</h2></a>'.encode("latin-1")
    e = entradas_portada(html, "https://www.lavozdegalicia.es/")
    assert e[0]["titulo"] == "La Xunta aprueba los presupuestos de 2027 con cambios"


def test_descripcion_video_sin_ruido():
    from pyxis.recolector import descripcion_video
    d = ("¡Invierte con X! Utiliza mi enlace: https://x.y/z Patrocinador\n"
         "Ucrania avanza quince kilómetros por un gasoducto en Kupiansk. Analizamos qué significa.\n"
         "00:00 Introducción\nSígueme en Instagram")
    assert descripcion_video(d) == "Ucrania avanza quince kilómetros por un gasoducto en Kupiansk. Analizamos qué significa."


def test_puente_quita_ruido():
    from pyxis.puente import es_ruido
    assert es_ruido({"url": "https://www.20minutos.es/deportes/tenis/alcaraz_1.html"})
    assert es_ruido({"url": "https://www.antena3.com/programas/la-voz/x.html"})
    assert not es_ruido({"url": "https://www.eldiario.es/politica/sanchez-debate_1_2.html"})
