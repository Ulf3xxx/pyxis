import datetime as dt

from pyxis.grafica import grafica_svg
from pyxis.mercados import parsear, resumen


def test_parsear_fred_y_bce():
    fred = "observation_date,SP500\n2026-11-18,6000.5\n2026-11-19,.\n2026-11-20,6010\n"
    assert parsear("fred", fred) == [(dt.date(2026, 11, 18), 6000.5), (dt.date(2026, 11, 20), 6010.0)]
    bce = "KEY,FREQ,TIME_PERIOD,OBS_VALUE\nEXR.D,D,2026-11-19,1.0998\nIRS.M,M,2026-10,3.1\n"
    assert parsear("bce", bce) == [(dt.date(2026, 10, 1), 3.1), (dt.date(2026, 11, 19), 1.0998)]


def test_resumen_y_grafica():
    datos = [(dt.date(2025, 11, 20) + dt.timedelta(days=i), 100 + i) for i in range(366)]
    r = resumen(datos)
    assert r["fecha"] == "2026-11-20" and r["var_anterior"] == round((465 / 464 - 1) * 100, 2)
    svg = grafica_svg([("X", datos)], "Prueba", "Puntos", "pie", "FRED")
    assert svg.startswith("<svg") and "Prueba" in svg and "Fuente: FRED" in svg


def test_parsear_bde():
    from pyxis.mercados import parsear_bde
    t = '"CÓDIGO DE LA SERIE",A,DBLEESI100000000IBDI.B\n"FRECUENCIA","LABORABLE","LABORABLE"\n"19 NOV 2026",1.0,15880.5\n"20 NOV 2026",1.1,_\n"FUENTE","X","Y"\n'
    assert parsear_bde(t, "DBLEESI100000000IBDI.B") == [(dt.date(2026, 11, 19), 15880.5)]
