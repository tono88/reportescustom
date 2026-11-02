# Investigación funcional y diseño Tecnodyne

Fecha: 2 de noviembre de 2026. Método: revisión de ficha pública y guía funcional del fabricante, contrastadas con el código público de Odoo 18 instalado localmente. No se adquirió, descompiló ni inspeccionó código de Ksolves; no se validó su demo autenticada. Las capacidades anunciadas son evidencia comercial, no mediciones independientes.

## Capacidades observadas

La [ficha de Odoo 18](https://apps.odoo.com/apps/modules/18.0/ks_dashboard_ninja) anuncia KPI, listas, barras verticales/horizontales, líneas, áreas, pastel, dona, polar, flor, embudo, radial, radar, dispersión, bullet, mapa y tareas. Incluye filtros, metas, personalización, permisos, multicompañía, idiomas, monedas, exportación Excel/CSV/PDF/PNG, intercambio de configuraciones, navegación de detalle, actualización y generación/interpretación con IA. También publica favoritos, chat por indicador, datos desde archivos y cambio de visualización. La enumeración principal dice 17 tipos y una FAQ dice 18: esa discrepancia impide usar el número como especificación contractual. Las plantillas sectoriales se anuncian como pagadas. La ficha identifica licencia OPL-1.

La [guía funcional](https://www.ksolves.com/user-guide/odoo-dashboard-ninja/) describe modelo y medida por indicador, dominios, subagrupación, orden, límites, agrupación temporal, fechas por indicador, comparación con períodos anteriores, filtros predefinidos y personalizados, paleta y múltiples layouts. Enumera 28 rangos de fechas mientras la ficha menciona 20. Su texto incluye varias versiones antiguas: debe comprobarse cada función en la versión objetivo. Se toma el comportamiento general como referencia, no nombres internos ni estructuras de almacenamiento.

El [catálogo del fabricante](https://store.ksolves.com/shop/product/dashboard-ninja-with-ai-v-16.0) también anuncia soporte Community/Enterprise/Odoo.sh, unidades y filtros de usuario/empresa. Es una página de otra versión, por lo que solo sirve como corroboración general. [Dashboard Ninja Advance](https://ksolvesstore17stage.kappso.com/shop/product/advanced-dashboard-ninja-with-ai-v-18.0) anuncia envío de snapshots PDF por correo: no se atribuye automáticamente al módulo base solicitado.

## Matriz histórica de la primera entrega 18.0.1.0.0

Esta sección conserva el diagnóstico inicial. La implementación actual 18.0.2.0.0 y sus pruebas se describen en [PARIDAD.md](PARIDAD.md); los pendientes de esta tabla no representan el estado actual.

| Área | Estado 18.0.1.0.0 | Próxima entrega propuesta |
|---|---|---|
| Visualizaciones | KPI, barras, líneas, pastel, tabla agrupada | Horizontal, área, dona; después radar/dispersión/embudo y mapa |
| Cálculo | Conteo, suma, promedio, mínimo, máximo | Segundas medidas y subgrupos |
| Selección | Modelo, dominio JSON y tokens propios | Editor visual de dominios y validación interactiva |
| Tiempo | Rango manual global, campo por indicador, agrupación día/año | Presets, comparaciones, relleno de períodos vacíos |
| Detalle | Abrir registros de KPI/grupo con permisos actuales | Jerarquías de exploración configurables |
| Diseño | Rejilla adaptable, orden por secuencia, marca Tecnodyne | Arrastrar, redimensionar, layouts personales, temas |
| Metas | Valor y porcentaje en KPI | Objetivos por período, semáforos, comparativas |
| Exportación | CSV de resultados visibles | XLSX completo paginado, PNG y PDF |
| Portabilidad | JSON versionado por nombres de modelo/campo | Validación previa, elementos individuales, migraciones de esquema |
| Permisos | Lector/diseñador, audiencia y empresa | Audiencia por indicador y favoritos personales |
| Actualización | Manual y sondeo | Invalidación selectiva por bus, métricas de carga |
| Datos externos | No implementado | Staging CSV/XLSX, mapeo, cuotas y trazabilidad |
| Colaboración | No implementado | Tareas y chatter con permisos propios |
| IA | No implementada; ninguna llamada externa | Proveedor opcional, propuestas revisables, sin SQL ejecutable |
| Idiomas/moneda | Nombres traducibles y etiqueta de unidad | Catálogos completos y conversión con fecha/tasa explícita |
| Plantillas | Configuración manual | Ventas, compras, contabilidad, inventario, POS, manufactura y RRHH |
| Versiones | Implementación 18 | Rama 19 con batería completa; futuras versiones bajo validación |

## Arquitectura original

`tecnodyne.dashboard` almacena identidad, audiencia y compañía. `tecnodyne.dashboard.item` almacena consultas declarativas. `_query` determina contexto y permisos; `_payload` produce resultados; `action_drill` vuelve a calcular el dominio de detalle en servidor. El cliente OWL representa resultados y usa Chart.js ya incluido en Odoo. El asistente de transferencia evita IDs técnicos entre bases y permite un esquema de evolución explícito.

Referencias de plataforma: [ORM de Odoo 18](https://www.odoo.com/documentation/18.0/developer/reference/backend/orm.html), [componentes OWL](https://www.odoo.com/documentation/18.0/developer/reference/frontend/owl_components.html). Las páginas no respondieron durante esta sesión; las APIs utilizadas se contrastaron con el código de la instalación local 18.0-20250924 y pruebas reales.

## Orden de evolución y aceptación

1. Consolidar el núcleo: verificar instalación, permisos, aislamiento y exactitud con datos de Bloquera/Ferretería. Definir indicadores y monedas antes de preparar plantillas.
2. Completar filtros y análisis: orden explícito, subgrupos, comparaciones temporales y agregados verificados contra vistas nativas. Probar zonas horarias, valores negativos, grupos vacíos y volúmenes reales.
3. Completar experiencia y exportaciones: persistencia del layout por usuario, accesibilidad, formatos descargables y pruebas de contenido/límites de cada exportación.
4. Añadir fuentes externas y colaboración como módulos opcionales; las importaciones deben tener staging separado y errores recuperables.
5. Añadir IA como extensión desacoplada: el usuario revisa la propuesta, solo se aceptan modelos/campos autorizados y nunca se ejecuta código generado. Definir explícitamente qué datos saldrían del servidor antes de conectar un proveedor.
6. Migrar a 19: rama propia, revisar cambios de API y assets, instalar en base limpia y repetir permisos, cálculos y QA visual. Repetir el proceso en cada versión futura.

No es posible deducir algoritmos internos, calidad de IA, rendimiento o paridad completa a partir de la página. Esta entrega establece una alternativa ejecutable y una especificación de evolución verificable; no promete equivalencia total ni compatibilidad automática con versiones aún no probadas.
