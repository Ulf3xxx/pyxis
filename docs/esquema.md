# Esquema de datos

Todo en Pyxis son documentos JSON. Este esquema es el puente entre la hemeroteca original y el programa independiente: si un documento lo cumple, cualquiera de las dos partes puede leerlo.

| Documento | Para qué sirve | Estado |
|---|---|---|
| [Edición](#edición) | Un resumen de noticias de un momento del día | **En uso** (versión 1) |
| [Hecho](#hecho-borrador) | Una afirmación comprobable extraída de una noticia | Borrador |
| [Hilo](#hilo-borrador) | Un asunto que se sigue a lo largo del tiempo | Borrador |
| [Relación](#relación-borrador) | Un vínculo entre hechos o hilos | Borrador |
| [Radar](#radar-borrador) | El informe semanal de riesgos y oportunidades | Borrador |

Los borradores describen la intención. Pueden cambiar hasta que haya código que los use.

## Edición

Identificador: `AAAA-MM-DD-<edicion>`, por ejemplo `2026-11-16-manana`. Un archivo por edición.

### Campos de primer nivel

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `fecha` | texto `AAAA-MM-DD` | sí | Día de la edición |
| `edicion` | `manana`, `mediodia`, `noche` o `prueba` | sí | Momento del día |
| `hora` | texto `HH:MM` | sí | Hora local de cierre |
| `titulo` | texto | sí | Título visible |
| `resumen` | texto | sí | Una frase con lo más importante |
| `destacados` | lista de textos | sí | Titulares principales |
| `temas` | lista de textos | sí | Palabras clave para buscar: países, personas, empresas, asuntos |
| `noticias` | lista de `{seccion, titular}` | no | Índice plano de titulares, para listar y buscar sin abrir el contenido |
| `contenido` | objeto | sí* | El cuerpo de la edición (ver abajo) |
| `url` | texto | no | Solo en ediciones antiguas: enlace a la página donde se publicó |
| `base` | texto | no | En ediciones de mediodía y noche construidas por actualización: identificador de la edición de la que parten, por ejemplo `2026-11-19-manana` |

\* Las ediciones anteriores al 13 de noviembre de 2026 no tienen `contenido`: guardan solo el índice y `url`. El validador las acepta con un aviso.

### `contenido`

| Campo | Tipo | Descripción |
|---|---|---|
| `esencial` | lista de textos | Lo imprescindible, una línea por noticia |
| `secciones` | lista de secciones | En este orden: `geo`, `espana`, `internacional`, `economia`, `tecnologia` |
| `lecturas` | lista de `{fuente, titulo, url, resumen}` | Análisis recomendados |
| `videos` | lista de `{canal, titulo, url, fecha, descripcion}` | Vídeos relacionados |
| `revision` | lista de `{fuente, estado}` | Qué pasó con cada fuente consultada |
| `notas` | texto, opcional | Incidencias de la edición |

Cada **sección** tiene `id`, `nombre`, una `nota` opcional y su lista de `noticias`. Una sección puede quedar vacía si la `nota` explica por qué.

Cada **noticia** tiene:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `titular` | texto | sí | Titular propio, no copiado |
| `texto` | texto | sí | De dos a cuatro frases con los hechos verificados |
| `porque` | texto | sí | Una frase: por qué importa |
| `fuentes` | lista de `{nombre, url}` | sí, al menos una | De dónde sale cada dato |
| `como_lo_cuentan` | texto | no | Diferencias de encuadre entre medios |
| `actualizacion` | verdadero o falso | no | Si continúa una noticia de una edición anterior |
| `estado` | `nueva`, `actualizada` o `sin_cambios` | no | En ediciones por actualización: qué pasó con la noticia respecto a la `base` |

### Ediciones por actualización

Desde el 18 de noviembre de 2026, las ediciones de mediodía y noche no se redactan desde cero: copian la edición anterior del día (`base`), reescriben las noticias con novedades (`estado: "actualizada"`), añaden las nuevas (`estado: "nueva"`) y dejan el resto como estaba (`estado: "sin_cambios"`). Así cada edición es completa por sí misma y cuesta menos producirla.

`revision[].estado` admite cuatro valores:

- `leida`: se abrió y se leyó el artículo.
- `buscador`: solo se vio el título y el extracto en un buscador.
- `no_accesible`: no se pudo consultar.
- `sin_novedades`: se consultó y no había nada nuevo.

Hay un ejemplo completo, con datos ficticios, en [`ejemplos/edicion-ejemplo.json`](../ejemplos/edicion-ejemplo.json).

### Validar

```bash
python -m pyxis.validar RUTA
```

Los errores indican que el documento no cumple el esquema. Los avisos señalan cosas que conviene revisar, como que el índice `noticias` y los titulares de `contenido` no coincidan.

## Hecho (borrador)

Una afirmación concreta y comprobable, separada de la noticia que la contó. Es la pieza con la que se construye lo demás.

```json
{
  "id": "h-2026-11-16-001",
  "fecha": "2026-11-16",
  "afirmacion": "Una frase con un único hecho.",
  "tipo": "hecho | declaracion | cifra | previsto",
  "confianza": "alta | media | baja",
  "fuentes": [{"nombre": "Medio", "url": "https://…"}],
  "edicion": "2026-11-16-manana",
  "hilos": ["id-del-hilo"],
  "entidades": ["país, persona, empresa o institución"]
}
```

`tipo` distingue lo que ocurrió (`hecho`) de lo que alguien dijo (`declaracion`), de un dato numérico (`cifra`) y de algo anunciado que aún no ha pasado (`previsto`).

## Hilo (borrador)

Un asunto que dura días o meses. Agrupa hechos y permite ver su evolución.

```json
{
  "id": "ejemplo-de-hilo",
  "nombre": "Nombre corto del asunto",
  "descripcion": "Qué se sigue y por qué.",
  "estado": "abierto | latente | cerrado",
  "desde": "2026-11-11",
  "actualizado": "2026-11-16",
  "ambitos": ["geopolitica", "energia"],
  "hechos": ["h-2026-11-16-001"]
}
```

## Relación (borrador)

Un vínculo entre dos hechos o hilos. Aquí vive la parte de razonamiento, y por eso cada relación declara si es un hecho documentado o una inferencia.

```json
{
  "id": "r-0001",
  "origen": "id de hecho o hilo",
  "destino": "id de hecho o hilo",
  "tipo": "causa | condiciona | contradice | precede | afecta_a",
  "naturaleza": "documentada | inferida",
  "explicacion": "Por qué se relacionan, en una o dos frases.",
  "fuentes": [{"nombre": "Medio", "url": "https://…"}],
  "confianza": "alta | media | baja"
}
```

Una relación `documentada` necesita una fuente que la afirme. Una `inferida` es una hipótesis de Pyxis y se muestra siempre como tal.

## Radar (borrador)

El informe semanal. Parte de los hilos abiertos y propone qué vigilar según los ámbitos que interesan a quien lo usa.

```json
{
  "id": "radar-2026-S47",
  "semana": "2026-W47",
  "ambitos": ["vision-geopolitica", "arquitectura-y-construccion"],
  "senales": [
    {
      "titulo": "Qué está cambiando",
      "hilos": ["ejemplo-de-hilo"],
      "cadena": ["hecho", "consecuencia intermedia", "efecto en el ámbito"],
      "lectura": "riesgo | oportunidad | incierto",
      "horizonte": "semanas | meses | años",
      "confianza": "alta | media | baja",
      "que_vigilar": ["indicador o acontecimiento que confirmaría o desmentiría la señal"]
    }
  ],
  "notas": "Límites del análisis de esta semana."
}
```

El radar ordena información para pensar. No recomienda inversiones ni sustituye el consejo de un profesional.

## Vídeos de YouTube junto a las noticias

Desde el 21 de noviembre de 2026, los vídeos de los canales que sigue el recolector se clasifican con el resto de la información, no en un bloque aparte.

- `noticia.videos`: vídeos que tratan esa noticia.
- `seccion.videos`: vídeos de la sección que no encajan en ninguna noticia; llevan además `tema`.

Cada vídeo: `canal`, `titulo` (original), `url`, `fecha` (AAAA-MM-DD), `trata` (de qué trata, una frase) y `postura` (opinión o enfoque que presenta el canal, una frase, atribuida). Se elaboran a partir del título y la descripción del vídeo, sin visionarlo: la página lo indica. `contenido.videos` (el antiguo bloque «Para ver») queda solo para ediciones anteriores.
