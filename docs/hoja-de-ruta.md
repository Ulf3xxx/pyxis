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
| 3 | Exportar el archivo | Las ediciones y la configuración, guardadas como archivos JSON | Hecho (primera exportación) |
| 4 | Sincronización continua | Cada edición nueva se guarda también como archivo, sin copiar a mano | Siguiente |
| 5 | Visor independiente | Página web estática con buscador que lee los archivos JSON | Pendiente |
| 6 | Recolector propio | Lectura de fuentes por RSS y páginas abiertas, con registro de qué fuente es accesible | Pendiente |
| 7 | Motor de ediciones | Redacción con un modelo de lenguaje intercambiable (de pago o local) | Pendiente |
| 8 | Capa de conocimiento | Hechos, hilos y relaciones; radar semanal | Pendiente |
| 9 | Servicio | Instalación sencilla, acceso para un grupo pequeño, documentación | Pendiente |

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
