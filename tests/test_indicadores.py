from pyxis.indicadores import construir, fecha


def test_fecha():
    assert fecha("2025") == "20250701"
    assert fecha("2026-03") == "20260315"
    assert fecha("2026-Q2") == "20260515"
    assert fecha("2026-S2") == "20261001"


def test_construir_tabla_y_union():
    inf = {"indicadores": {"a": {"datos": {"ES": {"2018": 1.0, "2025": 2.0}, "EU27_2020": {"2025": 3.0}}},
                           "b": {"datos": {"ES": {"2026": 5.0}, "EU27_2020": {"2026": 6.0}}}}}
    cfg = {"referencia": "2018", "series": [{"id": "x", "clave": "a", "titulo": "X", "unir": [{"clave": "b", "desde": "2026"}]}]}
    res = construir(cfg, [inf])
    fila = res["tabla"][0]
    assert (fila["valor_referencia"], fila["ultimo_periodo"], fila["ultimo"], fila["ue_ultimo"]) == (1.0, "2026", 5.0, 6.0)
    assert res["series"]["x"]["comparar_nombre"] == "UE-27"
