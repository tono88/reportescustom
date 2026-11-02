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

No se ejecutó inferencia contra un modelo real: Ollama debe instalarse/configurarse para esa prueba. Tampoco se ejecutó Odoo 19, Enterprise, Odoo.sh, una prueba de carga o una conciliación contra los datos reales de Bloquera/Ferretería. La página comercial no permite certificar rendimiento, calidad de IA ni equivalencia visual exacta.

## Repetición

Ejecutar en una base de pruebas con directorio de datos escribible, el directorio padre del módulo en `addons_path` y parámetros `-i tecnodyne_dashboard --without-demo all --test-enable --test-tags /tecnodyne_dashboard --stop-after-init`. Para una base ya instalada usar `-u`.

Antes de activar indicadores financieros, comprobar sus dominios/estados, fechas y moneda contra informes nativos. Las plantillas son puntos de partida configurables.
