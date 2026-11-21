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
    assert r["fecha"] == "2026-11-20" and r["var_1d"] == round((465 / 464 - 1) * 100, 2)
    svg = grafica_svg([("X", datos)], "Prueba", "Puntos", "pie", "FRED")
    assert svg.startswith("<svg") and "Prueba" in svg and "Fuente: FRED" in svg
