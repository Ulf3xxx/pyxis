# Hoja de ruta

Pyxis avanza por dos vías a la vez:

- **Vía A, el laboratorio.** La hemeroteca original, que sigue generando tres ediciones diarias. Sirve para probar ideas con rapidez.
- **Vía B, el programa.** Este repositorio. Recoge lo que funciona en la vía A y lo convierte en software que no depende de ningún proveedor.

El [esquema de datos](esquema.md) es lo que las une.

## Pasos

| # | Paso | Resultado | Estado |
|---|---|---|---|
| 1 | Nombre, licencia y repositorios | Pyxis, AGPL-3.0, un repositorio público de código y uno privado de datos | Hecho |
| 2 | Esquema de datos y validador | Formato documentado y comprobable | Hecho (edición); borradores del resto |
| 3 | Exportar el archivo | Las ediciones y la configuración, guardadas como archivos JSON | Hecho: 21 ediciones, comprobadas byte a byte con la Hemeroteca |
| 4 | Sincronización continua | Cada edición nueva se guarda también como archivo, sin copiar a mano | Hecho: copia diaria a las 21:12 (hora de Madrid) |
| 5 | Visor independiente | Página web estática con buscador que lee los archivos JSON, con hilos básicos | Siguiente |
| 6 | Recolector propio | Lectura de fuentes por RSS y páginas abiertas, con registro de qué fuente es accesible | En marcha: 83 fuentes (RSS, Bluesky, portadas y 22 canales de YouTube por su API), cada tres horas; series de mercado diarias (FRED, BCE, Banco de España y Alpha Vantage) |
| 7 | Motor de ediciones | Redacción con un modelo de lenguaje intercambiable (de pago o local) | Pendiente |
| 8 | Capa de conocimiento | Hechos, hilos y relaciones; agrupación de titulares por historia con barra de espectro y rasgos de sesgo; radar semanal con mapas | Pendiente |
| 9 | Servicio | Instalación sencilla, acceso para un grupo pequeño, documentación | Pendiente |

## Cambios de funcionamiento (18 de noviembre de 2026)

- La edición de la mañana parte de los titulares del recolector antes de buscar.
- Las ediciones de mediodía y noche ya no se redactan desde cero: copian la edición anterior del día y solo añaden novedades o actualizan noticias (campos `base` y `estado`, ver el [esquema](esquema.md)). Dos subagentes en lugar de cuatro.

## Estado a 23 de noviembre de 2026

- Las ediciones usan el recolector desde el 19 de noviembre, a través de una tarea puente que copia las listas a la base de datos de la Hemeroteca. Las fuentes marcadas como no accesibles bajaron de unas 30 a menos de 10 por edición.
- Los vídeos de YouTube van junto a las noticias, con de qué tratan y la postura del canal (desde el 21 de noviembre).
- Gráficas de mercado en las noticias de economía (desde el 22 de noviembre).
- Bolsamanía como fuente principal de Economía (desde el 23 de noviembre).
- Uso de GitHub Actions: unos 25 minutos al día (algo más de un tercio del límite gratuito).

## Orden de trabajo (revisado el 23 de noviembre de 2026)

1. Consolidar: revisar unos días las ediciones con vídeos, gráficas y Bolsamanía; quitar ruido de los feeds (deporte, televisión, ofertas) usando feeds de sección.
2. Equilibrar el panel en el recolector. Hecho el 23 de noviembre: los 27 medios del panel llegan al recolector (El País, Público, Cadena SER, El Periódico y EFE por sus cuentas de Bluesky; RTVE, Vozpópuli, Antena 3 Noticias, laSexta Noticias y El Independiente por sus portadas). Las listas de las ediciones ya no llevan deporte, televisión, ocio ni compras.
3. Agrupar los titulares del recolector por historia. Hecho el 23 de noviembre: `pyxis/historias.py` agrupa los titulares del panel de las últimas 24 horas (TF-IDF y coseno, sin dependencias) y mide qué proporción de cada grupo cubre cada historia; el puente lo pasa a las ediciones en la lista «historias» y la Hemeroteca vuelve a mostrar la barra de espectro y los puntos ciegos. Pendiente: revisar la calidad de la agrupación unos días (a veces une o parte historias) y, sobre esta base, los rasgos de sesgo.
4. Hilos: seguir una historia a lo largo de los días en la Hemeroteca.
5. Radar semanal con mapas.
6. Visor independiente y motor de ediciones intercambiable (pasos 5 y 7).

## Líneas de trabajo añadidas

- **Rasgos de sesgo por titular.** Medir rasgos observables de cada titular según el medio (lenguaje cargado, atribución de las declaraciones, actor que aparece como sujeto, qué medios cubren o callan la historia), mostrados como rasgos con su motivo, nunca como veredicto. Instrucciones abiertas y adaptadas al español, comprobadas contra una muestra etiquetada a mano. Depende de agrupar titulares por historia. Referencias en [referencias.md](referencias.md#medir-el-sesgo).
- **Mapas temáticos.** Mapas al estilo de El Orden Mundial para hilos bien documentados: el modelo propone qué dibujar a partir de hechos verificados y el código dibuja el mapa (SVG con datos de Natural Earth). Primero en el visor y el radar semanal. Referencias en [referencias.md](referencias.md#mapas).

## Decisiones tomadas

- **Lenguaje:** Python, sin dependencias mientras sea posible.
- **Almacenamiento:** archivos JSON como formato de intercambio; SQLite cuando haga falta consultar.
- **Visor:** web estática, que se pueda alojar en cualquier sitio.
- **Modelo de lenguaje:** intercambiable. Pyxis no debe depender de un proveedor.
- **Datos fuera del código:** el archivo de noticias no se publica en este repositorio.

## Preguntas abiertas

- Cómo cubrir las fuentes que no ofrecen RSS ni permiten lectura automática, sin saltarse sus condiciones.
- Qué parte del archivo se puede compartir con un grupo y en qué condiciones. Publicar resúmenes de noticias tiene implicaciones legales que conviene consultar con un profesional antes de abrirlo a más gente.
- Cómo medir la calidad de una edición para comparar modelos de lenguaje.
