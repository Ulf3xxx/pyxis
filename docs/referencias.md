# Referencias: proyectos de los que aprender

Recopilación del 16 de noviembre de 2026. Punto de partida: el tema [geopolitical-analysis](https://github.com/topics/geopolitical-analysis) de GitHub y búsquedas de proyectos parecidos.

> **Sin verificar a fondo.** Las licencias y el número de estrellas proceden de buscadores y fichas de terceros, no de la lectura directa de cada repositorio. Antes de reutilizar código de cualquiera de estos proyectos hay que abrir su repositorio y confirmar la licencia.

## Conclusión

- **No reconstruir un visor geopolítico completo.** World Monitor ya lo hace, es AGPL-3.0 y ofrece conectores. Conviene usarlo como fuente.
- **Lo que Pyxis aporta de distinto:** archivo en el tiempo (hemeroteca), hilos que siguen un asunto, español y medios españoles, y un radar personal por ámbito.
- **GDELT no sirve como fuente principal, al menos con su API gratuita.** Ver la prueba más abajo.

## Visores de acontecimientos geopolíticos

| Proyecto | Qué hace | Qué nos sirve |
|---|---|---|
| [World Monitor](https://github.com/koala73/worldmonitor) | Panel global: cientos de feeds, resúmenes por IA, decenas de proveedores de datos, mapa por capas. AGPL-3.0. Tiene servidor MCP, CLI y bibliotecas para Python, Ruby y Go | Usarlo como fuente del radar. Su jerarquía de fuentes por niveles (agencias y canales oficiales, grandes cadenas, medios especializados) es un modelo para nuestro registro de fuentes |
| IntelHQ (laikhtman) | Panel que combina ACLED, UCDP, ACNUR y GDELT con más de 150 feeds | Lista de fuentes de datos de conflicto |
| [Pharos AI](https://github.com/Juliusolsson05/pharos-ai) | Panel centrado en un conflicto. Parte de que las plataformas OSINT muestran hechos sueltos pero no el cuadro completo | Es el mismo problema que quieren resolver nuestros hilos |
| World Watch (nergalith) | Agregador público que se actualiza con una tarea programada de GitHub a partir de GDELT, ONU y Crisis Group | El mismo montaje sin servidor que planeamos |
| [ShadowBroker](https://github.com/BigBodyCobain/Shadowbroker) | Barcos, satélites, vuelos y conflictos sobre un mapa | Poco: es de sensores, no de contexto |
| [OSINT War Room](https://github.com/Hue-Jhan/OSINT-War-Room) | Panel táctico con GDELT, mercados y vuelos | Ejemplo de integración de GDELT en Python |

Del tema geopolitical-analysis (proyectos pequeños, de 1 a 11 estrellas):

- **asadmukhtar220/macropulse:** de feeds RSS a acontecimientos macro asignados a sectores. Misma idea que nuestra cadena «hecho → efecto en el ámbito».
- **Future3lab/iran-skill:** paquete de análisis en formato «skill». Ejemplo de cómo empaquetar un método de análisis.
- **Polityra/Open-Polityra:** herramientas de análisis y evaluación de escenarios.
- **in6lack/seldon-vault:** previsión con varios agentes de IA.

## Parecidos a la hemeroteca

| Proyecto | Qué hace | Qué nos sirve |
|---|---|---|
| [Horizon](https://github.com/Thysrael/Horizon) | Recoge de RSS y otras fuentes, puntúa con IA, quita repetidos y genera un resumen diario. Python, MIT, con plantilla de GitHub Actions | El patrón más cercano para los pasos 6 y 7 (recolector y motor) |
| DailyBrief (leiting-eric) | Resumen diario que se ejecuta con GitHub Actions y produce un único archivo HTML | Modelo para el paso 5 (visor) |
| infinitum (shawnxie94) | Agrupa noticias relacionadas en un mismo acontecimiento y genera informes diarios | Referencia para agrupar por hilo |
| FeedMe (Seanium) | Lector con resúmenes por IA desplegable en GitHub Pages | Otro modelo de visor estático |
| [auto-news](https://github.com/finaldie/auto-news) | Agregador con Airflow, Milvus, Redis y MySQL | Ejemplo de la complejidad que queremos evitar |

## Conectores

| Conector | Qué da |
|---|---|
| [GDELT](https://www.gdeltproject.org) (API DOC 2.0) | Titulares y enlaces de prensa mundial en decenas de idiomas, sin clave. Ver `pyxis/sonda_gdelt.py` |
| [cyanheads/gdelt-mcp-server](https://github.com/cyanheads/gdelt-mcp-server) | Servidor MCP sobre GDELT; desglosa la cobertura por idioma o país |
| news-aggregator-mcp-server (aiagentkarl) | Servidor MCP que junta RSS, Hacker News y GDELT sin clave |
| [moltrus/google-news-mcp](https://github.com/moltrus/google-news-mcp) | Servidor MCP sobre los feeds de Google News |

## Prueba de GDELT (16 de noviembre de 2026)

Se consultó la API DOC 2.0 por cada uno de los 22 medios del panel desde una tarea de GitHub Actions, dos veces (ventanas de 24 y 72 horas, una consulta cada seis segundos como mínimo).

- **Límite de uso:** en la segunda pasada, 17 de 22 consultas recibieron un rechazo por exceso de peticiones (HTTP 429). Las máquinas de GitHub comparten dirección con muchos otros usuarios.
- **Cobertura escasa donde sí respondió:** entre 0 y 5 artículos por medio. El País y Europa Press devolvieron 2 artículos en 24 horas; infoLibre, Cadena SER y El Economista, ninguno en 72 horas.
- **Sin confirmar:** si otra forma de consulta (por país o idioma) devolvería más, y si desde una dirección propia el límite desaparece.

Conclusión: no apoyar el recolector en GDELT. Queda como fuente secundaria para medir volumen de cobertura, si se resuelve el límite de uso.

## Prueba de RSS (18 de noviembre de 2026)

Desde GitHub Actions, con `pyxis/sonda_rss.py`, respetando `robots.txt`:

- **Primera pasada:** 13 de 22 medios del panel con feed útil.
- **Segunda pasada:** siguiendo los directorios de feeds y direcciones conocidas, 14 de 22 (se suma El Confidencial). De 10 candidatos españoles, 6 con feed; de 19 extranjeros, 13.
- **Fuera por decisión de cada medio:** El País y RTVE prohíben leer sus feeds en `robots.txt`; Reuters lo prohíbe todo; El Economista, El Periódico, AP y otros rechazan la conexión.

Conclusión: el RSS sirve como base del recolector.

## Huecos: lo que no encontramos

- Un equivalente de código abierto a la comparación de cobertura por espectro ideológico (lo que hace Ground News).
- Proyectos de este tipo en español o centrados en medios españoles.

Los dos son espacios donde Pyxis puede aportar algo que no existe.
