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
| 6 | Recolector propio | Lectura de fuentes por RSS y páginas abiertas, con registro de qué fuente es accesible | Primera versión en marcha: 41 fuentes (RSS y Bluesky), cada tres horas |
| 7 | Motor de ediciones | Redacción con un modelo de lenguaje intercambiable (de pago o local) | Pendiente |
| 8 | Capa de conocimiento | Hechos, hilos y relaciones; agrupación de titulares por historia con barra de espectro y rasgos de sesgo; radar semanal con mapas | Pendiente |
| 9 | Servicio | Instalación sencilla, acceso para un grupo pequeño, documentación | Pendiente |

## Cambios de funcionamiento (18 de noviembre de 2026)

- La edición de la mañana parte de los titulares del recolector antes de buscar.
- Las ediciones de mediodía y noche ya no se redactan desde cero: copian la edición anterior del día y solo añaden novedades o actualizan noticias (campos `base` y `estado`, ver el [esquema](esquema.md)). Dos subagentes en lugar de cuatro.

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
