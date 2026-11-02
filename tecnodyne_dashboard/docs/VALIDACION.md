# Validación de Tecnodyne 18.0.2.0.0

Fecha: 2 de noviembre de 2026. Entorno: Windows, Odoo Community 18.0-20250924 y PostgreSQL local. Se usaron bases y usuarios de pruebas separados de la operación del negocio.

## Servidor

Instalación limpia, actualizaciones reales del módulo y **28 pruebas aprobadas, 0 fallos y 0 errores**:

- Aislamiento de empresas, ACL de fuentes, audiencia de tablero/indicador, rechazo de escritura a lectores y privacidad de diseños.
- Payloads de los 18 tipos de elemento; rangos temporales, zona horaria Guatemala, huecos y acumulados, comparación de períodos.
- Agrupación, subgrupos, medidas adicionales, jerarquía de detalle, rutas inválidas y paginación sin cambiar el dominio del registro.
- Conversión monetaria USD/EUR antes de agregar; KPI porcentual y rechazo de referencias cíclicas.
- CSV/Excel con más filas que el límite de pantalla y tratamiento de cadenas que parecen fórmulas.
- Importación CSV y reemplazo de fuente; JSON de ida/vuelta con datasets y consultas KPI dependientes.
- Tareas, notas, creación de conversación privada y revocación de acceso al canal.
- Evento de actualización sin valores de negocio; contrato Ollama simulado y generación sin enviar registros.
- Renderizado QWeb del informe.

## Navegador real

Chrome con Odoo local: **18 tarjetas, 14 canvas, 0 errores de JavaScript**. Se verificaron:

- Carga del tablero y los tipos de gráficos con Chart.js real y renderizadores propios.
- Descargas XLSX, PNG y PDF; el PDF generado comienza con la firma `%PDF`.
- Activación de edición, guardado de diseño personal y lista de tareas.
- Apertura del formulario y del editor visual de dominios.
- Actualización real por WebSocket: modificar un valor de la fuente cambió el KPI sin pulsar Actualizar; después se restauró el valor de prueba. También se verificaron assets y catálogos iniciales inglés/español.

Los archivos de QA quedan fuera del módulo distribuido. La biblioteca Sass de Odoo compiló la hoja de estilo y se comprobó la sintaxis JavaScript. Los contornos Natural Earth están incluidos localmente.

## Límites de esta validación

En la validación inicial no se ejecutó inferencia real; las pruebas posteriores con LM Studio se detallan abajo. No se ejecutó Odoo 19, Enterprise, Odoo.sh, una prueba de carga o una conciliación contra los datos reales de Bloquera/Ferretería. La página comercial no permite certificar rendimiento, calidad de IA ni equivalencia visual exacta.

## Repetición

Ejecutar en una base de pruebas con directorio de datos escribible, el directorio padre del módulo en `addons_path` y parámetros `-i tecnodyne_dashboard --without-demo all --test-enable --test-tags /tecnodyne_dashboard --stop-after-init`. Para una base ya instalada usar `-u`.

Antes de activar indicadores financieros, comprobar sus dominios/estados, fechas y moneda contra informes nativos. Las plantillas son puntos de partida configurables.

## Adaptador LM Studio — 18.0.2.0.1

Resultado de instalación/actualización y pruebas: **31 aprobadas, 0 fallos y 0 errores**. Se añadieron pruebas del formato Chat Completions, JSON Schema, token opcional, normalización de URL, consulta de modelos, rechazo de embeddings y detección de respuestas truncadas. Las respuestas de generación están simuladas. La API local de LM Studio respondió en el puerto 1234; en el momento de la comprobación solo anunciaba el modelo de embeddings, por lo que no se ejecutó generación real con Qwen.

## Corrección de razonamiento y espera — 18.0.2.0.2

El registro aportado mostró desconexión exactamente a los 180 segundos mientras el modelo seguía generando razonamiento. Se añadió modo nativo LM Studio con razonamiento desactivado por petición, almacenamiento desactivado, presupuesto de salida acotado y selección de cantidad de indicadores. Los errores de espera, conexión y ausencia de respuesta final tienen mensajes diferentes. No se usa el contenido de razonamiento como propuesta.

Resultado final de la batería: **34 aprobadas, 0 fallos y 0 errores**. Se añadieron casos de modo nativo, separación de razonamiento/respuesta final, delimitadores Markdown, tiempos de espera y tipos de campos inválidos antes de aplicar una propuesta.

Prueba real de API nativa con Qwen 3.5 4B: respuesta JSON simple en 1,1 segundos, cero tokens de razonamiento reportados por el servidor. Prueba real de Odoo: generar propuesta de un KPI de contactos, validar sus campos, aplicar y leer el tablero en 2,3 segundos. La transacción de prueba se revirtió al finalizar; no se creó un tablero permanente ni se modificó la configuración del negocio. Las duraciones corresponden a solicitudes pequeñas concretas.

## Semántica, consultas y playlist — 18.0.3.0.0

El KPI de contactos de la prueba anterior solo acreditaba el recorrido técnico de generación/aplicación. No probaba que una petición de ventas se interpretara correctamente. Se reprodujo y corrigió la aceptación de un conteo genérico para una petición mensual de categorías vendidas.

En una base aislada con Sales y POS instalados: **55 pruebas aprobadas, cero fallos y errores**. El ejecutor priorizó el código del repositorio para evitar que la copia antigua instalada en Windows ocultara los cambios.

- Pedidos de venta reales creados y confirmados: enero categoría B=8, febrero categoría A=9. El Top 1 mensual devuelve esas cifras; cantidades 999 de borradores/cancelaciones quedan excluidas.
- Órdenes POS reales: enero B=7, febrero A=11, con borradores/cancelados excluidos. Se valida la generación de dos indicadores desde una petición que originalmente seleccionaba el catálogo de categorías.
- Tendencia mensual usa SUM e importe, con fecha como agrupación. Conteos no solicitados y propuestas desactualizadas se rechazan.
- Asientos publicados de una empresa aislada: apertura diciembre=100, enero=20, marzo=30 y borrador febrero=999. El saldo al cierre es 150; la consulta mensual entrega 120, 120 y 150, incluyendo el mes vacío. No es una reconstrucción de disponibilidad bancaria.
- SQL agrega y une fuentes autorizadas, ejecuta CTE/ventanas y lee columnas originales de archivos con `json_extract`. Se comprueban límites de ejecución, rechazo de escrituras/tablas externas/extensiones, empresa, ACL, parámetros y navegación a registros autorizados.
- JSON de ida/vuelta conserva SQL, datos/tipos importados, alcance temporal y orden de detalle. Un lector puede usar campos de agrupación con caché vacía sin acceder a datos elevados; un dominio sobre un campo restringido se rechaza.

En Chrome con el código nuevo: dos canvas separados con resultados de enero/febrero, cambio de tamaño con el puntero, persistencia tras recargar, apertura del asistente de mover/copiar, editor visual de filtros y formulario nuevo de generación. **Cero errores JavaScript**. Las operaciones de QA se hicieron en la base aislada; no se reinició el servicio ni se actualizaron los datos de negocio del usuario.

La [matriz de los once videos](PLAYLIST_AUDIT.md) identifica las capacidades implementadas y los ejemplos aún pendientes. La prueba de recetas deterministas no se presenta como una prueba de comprensión universal de LM Studio. No se ha conciliado con las ventas reales de Bloquera/Ferretería ni certificado Odoo 19 o posteriores.

Se repitió además la generación genérica real con LM Studio/Qwen 3.5 4B usando el prompt nuevo: propuesta, validación, aplicación y lectura de un KPI explícitamente solicitado de contactos en 3,0 segundos, con transacción revertida. La respuesta incluyó `interval: null` y `sort: null` para ese KPI; se corrigió y cubrió con prueba que esas opciones irrelevantes conservan los valores predeterminados requeridos por Odoo. Un intervalo desconocido se rechaza antes de aplicar.
