from pyxis.historias import agrupar, cobertura, lista_historias, punto_ciego

G = {"A": "izq", "B": "izq", "C": "centro", "D": "dcha", "E": "dcha"}


def e(medio, titulo, h="10"):
    return {"medio": medio, "titulo": titulo, "url": f"https://x/{medio}/{h}", "fecha": f"2026-11-23T{h}:00:00Z"}


def test_agrupa_misma_historia_y_separa_otra():
    E = [e("A", "Sánchez anuncia un impuesto a los ultrarricos"),
         e("C", "Sánchez anuncia un nuevo impuesto para ultrarricos de 2.000 millones", "11"),
         e("D", "El impuesto a ultrarricos que anuncia Sánchez", "12"),
         e("E", "Un árbol cae sobre una carrera en Barcelona", "13"),
         e("B", "Caída de un árbol durante una carrera popular en Barcelona", "14")]
    H = agrupar(E)
    assert sorted(len(h["medios"]) for h in H) == [2, 3]


def test_cobertura_normaliza_por_tamano_de_grupo():
    c = cobertura(["A", "C", "D"], G)
    assert c["por_grupo"] == {"izq": "1/2", "centro": "1/1", "dcha": "1/2"}
    assert (c["izq"], c["centro"], c["dcha"]) == (25, 50, 25)
    assert punto_ciego(c) is None
    assert punto_ciego(cobertura(["A", "B", "D"], G)) is None
    assert punto_ciego(cobertura(["D", "E", "X"], G)) is None  # solo 2 medios del panel
    G2 = dict(G, F="dcha")
    assert punto_ciego(cobertura(["D", "E", "F"], G2)) == "dcha"


def test_lista_historias_formato():
    E = [e(m, "Lanzan cócteles molotov contra la comisaría de Palencia") for m in ("A", "D", "E")]
    texto, n = lista_historias(E, dict(G, F="dcha"))
    assert n == 1 and texto.startswith("3 medios | izq 43 % · centro 0 % · dcha 57 % | (medios por grupo: izq 1/2, centro 0/1, dcha 2/3)")
    assert texto.endswith("A, D, E")
