# Tecnodyne Dashboards — Odoo 18 Community

Versión **18.0.2.0.1**, implementación original LGPL-3 para crear tableros de negocio sin Enterprise. Usa los módulos estándar `web`, `mail` y `bus`; las exportaciones/importaciones usan `xlsxwriter` y `openpyxl`. No contiene código, imágenes ni estilos del producto usado como referencia funcional.

## Capacidades

- Indicadores y tarjetas con dos consultas, comparación, suma, razón y porcentaje; metas numéricas o progreso.
- Barras, horizontales, líneas, áreas, pastel, dona, polar, radar, dispersión, flor, embudo, radial, bullet, mapa por coordenadas, tablas agrupadas, listas de registros y tareas.
- Medidas múltiples, subgrupos, detalle jerárquico, orden, multiplicadores, acumulados, períodos vacíos y metas por fecha.
- Editor visual de dominios, filtros con nombre, 28 opciones temporales y comparación con período/año anterior.
- Diseño adaptable, tres distribuciones iniciales, arrastrar/reordenar, ajustar ancho/alto y guardar variantes privadas por usuario. Cuatro paletas y tres estilos de tarjeta.
- Favoritos, menús por tablero y acción de inicio; edición rápida, duplicar y mover indicadores.
- ACL, audiencias por tablero/indicador y compañías. Ninguna consulta de datos de negocio utiliza `sudo` ni SQL libre.
- CSV/XLSX completos respecto al filtro y nivel consultado; PNG de cualquier indicador; PDF con gráfico y tabla. La exportación no se recorta al límite de pantalla.
- Transferencia JSON de tableros/indicadores, medidas, filtros, metas, tareas y dependencias entre KPI. Los datos de fuentes importadas se incluyen y sus referencias se reasignan en el destino.
- Fuentes CSV/XLSX con asignación de columnas y reemplazo/sincronización de datos; conversaciones privadas por indicador en Discuss; actualización por eventos y sondeo opcional.
- IA local con Ollama o LM Studio para proponer tableros/indicadores por modelo y palabras clave, y explicar resultados. Catálogos iniciales español/inglés y nombres traducibles.

La [matriz de cobertura](docs/PARIDAD.md) distingue implementación, evidencia y límites. La [validación](docs/VALIDACION.md) registra las pruebas realizadas.

## Instalación

1. Agregar el directorio padre a `addons_path`, reiniciar Odoo 18 y actualizar la lista de aplicaciones.
2. Instalar **Tecnodyne Dashboards**. Para actualizar desde la primera entrega, actualizar el módulo: la nueva versión añade campos, tablas, reglas y dependencias.
3. Asignar **Tecnodyne Dashboard Designer** al configurador y **Tecnodyne Dashboard Viewer** a los lectores. Los lectores pueden completar tareas y conversar, pero no cambiar consultas.
4. Crear un tablero para Bloquera y otro para Ferretería. Elegir empresa y audiencia; seleccionar la empresa en el selector de Odoo al abrirlo. Los grupos vacíos permiten a los lectores autorizados de esa empresa acceder al tablero/indicador.
5. Agregar indicadores, escoger modelo/tipo/cálculo y campos. El editor visual genera dominios JSON. La pestaña Analysis permite editar JSON avanzado, por ejemplo `[["user_id","=","$uid"]]` o `[["company_id","=","$company"]]`; también se admiten `%UID` y `%MYCOMPANY` como valores completos.
6. Elegir un campo fecha por indicador. Los que no tengan ese campo no responden al filtro temporal. Los extremos del rango son inclusivos; los DateTime respetan la zona horaria del usuario.
7. Para una plantilla elegir Ventas, CRM, Contabilidad, Inventario o POS y **Add template**. La aplicación fuente debe estar instalada. Las consultas iniciales son ejemplos que deben ajustarse a estados contables/comerciales del negocio; un total genérico de documentos no equivale a ventas facturadas.

## Uso

El clic en un grupo avanza por los campos de detalle configurados; al terminar abre los registros. **Volver** sube un nivel. Listas/tablas tienen paginación. Los botones de exportación conservan el filtro y nivel actuales, incluyendo todas sus filas hasta el límite explícito de exportación.

**Diseño y edición** activa el arrastre y los controles de ancho/alto. Guardar conserva el diseño personal; las variantes con nombre permiten alternar distribuciones. La configuración completa y la duplicación solo se muestran a diseñadores. Mover/copiar hacia otro tablero está en el menú del mismo nombre.

Un administrador de ajustes puede publicar un menú por tablero y su acción. Para usarlo como inicio, seleccionarla en Preferencias → Home Action. Los favoritos aparecen en el menú Favorites.

**Chat** abre una conversación privada del indicador en Discuss. Se verifican empresa y audiencia al entrar y se eliminan destinatarios con acceso revocado antes de enviar contenido nuevo. El formulario también conserva un hilo de notas.

## Archivos y portabilidad

CSV debe ser UTF-8; Excel debe ser `.xlsx`. La primera fila contiene encabezados. Asignar la columna de etiqueta y, opcionalmente, categoría, dos valores numéricos, fecha, coordenadas, importe monetario y código de moneda. Seleccionar un dataset existente para reemplazar sus filas manteniendo los indicadores vinculados. Los archivos no se vinculan automáticamente a una carpeta externa: cada sincronización requiere subir el archivo actualizado.

La transferencia JSON usa esquema 2 y admite configuraciones de esquema 1. Permite exportar un indicador con sus consultas KPI dependientes o un tablero completo. Importar crea un tablero nuevo en la empresa activa, o añade indicadores al tablero seleccionado. No copia grupos de seguridad ni diseños privados. Las acciones personalizadas necesitan un ID externo y deben existir en destino. Los modelos/campos de las fuentes Odoo deben estar instalados. Los datasets internos viajan con sus filas; trate el JSON exportado como datos de negocio.

## IA recomendada

**Si ya usas LM Studio**, no necesitas Ollama: selecciona LM Studio en los ajustes de IA y usa `http://127.0.0.1:1234/v1` con el identificador exacto de tu modelo cargado. Consultar [instrucciones de LM Studio](docs/LM_STUDIO.md). El botón de prueba de conexión comprueba la lista de modelos sin ejecutar inferencia.

Para el equipo revisado (aproximadamente 24 GB RAM y RTX 3050 Ti Laptop de 4 GB), comenzar con **Ollama + `qwen3.5:4b`**. La inferencia puede repartir memoria entre GPU y RAM; medir latencia antes de habilitar uso general. [Modelo oficial](https://ollama.com/library/qwen3.5%3A4b).

Para usar **Ollama**, instalarlo por separado y descargar el modelo con `ollama pull qwen3.5:4b`. En Ajustes → Tecnodyne AI seleccionar proveedor Ollama, URL `http://127.0.0.1:11434` y modelo `qwen3.5:4b`. No se instala ni descarga automáticamente. Un servidor en otra máquina requiere su dirección accesible y la configuración de red correspondiente.

La generación envía estructura de campos autorizados y la petición, muestra una propuesta y exige aplicarla antes de crear indicadores. Nunca ejecuta código/SQL generado. Las explicaciones envían los resultados visibles al servidor configurado; las respuestas deben distinguir observaciones de hipótesis. El proveedor se puede cambiar mediante URL/modelo compatibles con la [API Ollama](https://docs.ollama.com/api/generate). Las pruebas automáticas usan un servicio simulado; no sustituyen la prueba con un modelo instalado.

## Límites y versiones

Los tableros pertenecen a una empresa. Las fuentes con `company_id` excluyen filas sin empresa; las fuentes sin ese campo conservan sus reglas originales. Los importes monetarios se convierten por registro y fecha antes de agregar; las medidas Float no se convierten por poner una etiqueta de moneda. Máximo de 10.000 filas por exportación/fuente transferida o conversión monetaria, 200 filas visibles por página y 5 MB por archivo cargado. Si se excede el límite de exportación, se solicita acotar el filtro y no se entrega un archivo parcial.

El mapa utiliza una proyección de coordenadas con marcadores, valores y contornos Natural Earth incluidos en el módulo; no necesita un servicio de cartografía externo. El bus invalida resultados y el navegador vuelve a consultar con los permisos actuales. En Windows depende de que funcione el bus de Odoo; el sondeo es una alternativa disponible.

Esta entrega instala y se prueba en **Odoo 18**. No se certifica automáticamente en 19 o futuras versiones. El [registro oficial de cambios de Odoo 19](https://www.odoo.com/documentation/19.0/th/developer/reference/backend/orm/changelog.html) introduce cambios de ORM que requieren una rama y pruebas propias. Tampoco se ha validado aquí Enterprise u Odoo.sh.
