# Pyxis

**Pyxis** (la constelación de la Brújula) es una hemeroteca personal de código abierto: recoge la actualidad de fuentes variadas, la resume con las fuentes a la vista, la guarda como base de conocimiento y ayuda a relacionar los hechos con riesgos y oportunidades para decidir mejor.

> **Estado: fase inicial.** Hoy el repositorio contiene el esquema de datos y un validador. El resto está descrito en la [hoja de ruta](docs/hoja-de-ruta.md) y se irá construyendo por pasos.

## De dónde viene

Pyxis nace de una hemeroteca que funciona desde noviembre de 2026 como tarea programada de un asistente de IA: tres ediciones diarias (mañana, mediodía y noche) con secciones de geopolítica, España, internacional, economía y tecnología. Ese sistema sigue en marcha como laboratorio. Pyxis es su versión independiente: un programa que cualquiera pueda instalar, con el proveedor de IA que prefiera o con un modelo local.

Las dos vías comparten un mismo formato de datos, de modo que lo que produce una lo puede leer la otra.

## Qué hará

| Pieza | Qué hace | Estado |
|---|---|---|
| Esquema de datos | Define la forma de una edición, un hecho, un hilo, una relación y un radar | Edición: en uso. Resto: borrador |
| Validador | Comprueba que un archivo cumple el esquema | Disponible |
| Visor | Página web estática para leer y buscar en el archivo | Pendiente |
| Recolector | Guarda los titulares de las fuentes (RSS y cuentas públicas de Bluesky) | Disponible |
| Motor de ediciones | Redacta la edición con un modelo de lenguaje intercambiable | Pendiente |
| Capa de conocimiento | Hechos, hilos y relaciones entre noticias; radar semanal | Pendiente |

## Principios

1. **Fuentes a la vista.** Cada dato lleva la fuente de la que sale y su enlace. Si algo solo se conoce por un titular, se dice.
2. **Hechos e inferencias, separados.** Lo que pasó va por un lado; lo que podría significar, por otro y marcado como tal.
3. **Sin atajos con el acceso.** El recolector respeta `robots.txt` y las condiciones de cada sitio, y no intenta saltarse muros de pago ni bloqueos.
4. **Resumir, no copiar.** Pyxis parafrasea y enlaza al original; no reproduce artículos.
5. **No es asesoramiento financiero.** El radar señala riesgos y oportunidades para pensar, no recomienda comprar ni vender nada.
6. **Tus datos son tuyos.** El código es público; el archivo de noticias y la configuración personal viven aparte, donde tú decidas.

## Probarlo

Hace falta Python 3.10 o posterior. No tiene dependencias.

```bash
git clone https://github.com/Ulf3xxx/pyxis.git
cd pyxis
python -m pyxis.validar ejemplos/          # valida el ejemplo incluido
python -m unittest discover -s tests       # ejecuta las pruebas
```

Para validar tu propio archivo de ediciones:

```bash
python -m pyxis.validar /ruta/a/tus/ediciones
```

Para recoger titulares de una lista de fuentes (formato descrito en `pyxis/recolector.py`):

```bash
python -m pyxis.recolector fuentes.json carpeta_de_salida
```

## Estructura

```
pyxis/        código del programa: validador, sondas de fuentes y recolector
docs/         esquema de datos y hoja de ruta
ejemplos/     una edición de ejemplo con datos ficticios
tests/        pruebas automáticas
```

## Documentación

- [Esquema de datos](docs/esquema.md)
- [Hoja de ruta](docs/hoja-de-ruta.md)
- [Referencias: proyectos de los que aprender](docs/referencias.md)

## Licencia

Pyxis se publica bajo la [GNU Affero General Public License v3.0 o posterior](LICENSE) (AGPL-3.0-or-later). Puedes usarlo, estudiarlo, modificarlo y compartirlo. Si distribuyes una versión modificada, o la ofreces como servicio en la red, debes publicar tu código bajo la misma licencia.
