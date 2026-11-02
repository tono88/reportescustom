# Auditoría funcional de Tecnodyne 18.0.3.0.0

Actualización: la [auditoría de la playlist](PLAYLIST_AUDIT.md) precisa las carencias encontradas, recetas nuevas y límites. El generador anterior podía devolver conteos que no respondían a la petición; validar formato no demostraba corrección de negocio.

Revisión del 2 de noviembre de 2026. Referencias públicas: [ficha exacta Odoo 18](https://apps.odoo.com/apps/modules/18.0/ks_dashboard_ninja) y [guía del fabricante](https://www.ksolves.com/user-guide/odoo-dashboard-ninja/). Las páginas sirven para identificar requisitos; la implementación se acredita con código y pruebas propias. No se inspeccionó código propietario ni se verificó la demo autenticada.

La ficha y la guía difieren en cantidades y contienen ejemplos de distintas versiones. Se cubren las capacidades funcionales identificadas del producto base, sin asumir que se conoce cada detalle interno o que el rendimiento/IA es idéntico.

| Capacidad | Implementación Tecnodyne | Evidencia / límite |
|---|---|---|
| Tarjetas y KPI | `kind=kpi`, icono/color y tres estilos | Navegador, pruebas de conteo y fórmulas |
| Barras / horizontales | Chart.js | Navegador real |
| Línea / área | Chart.js con relleno | Navegador real |
| Pastel / dona / polar | Chart.js | Navegador real |
| Radar / dispersión | Chart.js, dos ejes numéricos | Navegador real |
| Flor / embudo | Dibujo canvas propio | Navegador real |
| Radial / bullet | Dibujo canvas propio, metas | Navegador real |
| Mapa | Coordenadas, valores y marcadores | Países Natural Earth incluidos; no requiere proveedor externo |
| Lista agrupada / registros | ORM y columnas configurables | Paginación y dominio de detalle probados |
| Tareas | Lista con estado persistente | Lector solo puede cambiar estado |
| Animación | Transiciones Chart.js y canvas | Interpolación en gráficos propios |
| Cálculos | Conteo/suma/promedio/mínimo/máximo | Pruebas de agregados |
| Medidas y subgrupos | Primaria, secundaria y medidas adicionales | Prueba de exportación multimedida |
| Medida como línea | Secundaria como línea sobre barras | Campo `secondary_as_line` |
| Acumulados | Valores acumulados o línea adicional | Prueba temporal con huecos |
| Selección | Modelo, dominio visual y JSON | Editor real en navegador |
| Orden / límite | Grupo/valor ascendente/descendente | Límite de página separado de exportación |
| Tiempo | 28 opciones y rango manual | Prueba de todos los rangos y zona Guatemala |
| Comparaciones | Período anterior / año anterior | Prueba con importes conocidos |
| KPI con dos consultas | Comparación/suma/razón/porcentaje | Prueba de porcentaje y bloqueo de ciclos |
| Metas | General y por fecha, número/progreso/línea | Datos de meta en cada período |
| Detalle | Jerarquía y regreso; luego registros | Ruta calculada en servidor, índice inválido rechazado |
| Acción alternativa | Acción Odoo configurada | Permisos de la acción se conservan |
| Multitablero | CRUD y archivo estándar | Modelo y vistas nativas |
| Layout | Tres plantillas, arrastre, ancho/alto | Guardado probado en navegador |
| Variantes privadas | Layouts con nombre por usuario | Propiedad no reasignable, prueba de aislamiento |
| Presentación | Cuatro paletas, icono/color, leyenda/valores | Opciones por indicador |
| Formatos numéricos | Estándar/compacto/indio/científico | `Intl.NumberFormat` |
| Edición inmediata | Nombre/color/tipo y formulario | Solo diseñadores escriben |
| Cambio de gráfico | Cambio compatible conservando resultados | No convierte una tarea en datos numéricos |
| Favoritos | Preferencia privada y menú | Modelo con regla de propietario |
| Menú / inicio | Acción publicada por administrador | Seleccionable en Home Action de Odoo |
| Duplicar / mover | Tablero estándar y asistente de indicadores | Verifica destino y permisos de escritura |
| Seguridad | Lector/diseñador y audiencias por elemento | ACL, empresas y fuentes probadas |
| Empresas | Contexto acotado y reglas de compañías | Un tablero por empresa |
| Idiomas / RTL | Infraestructura Odoo y catálogos es/en | Catálogos iniciales, no traducción de todos los idiomas |
| Monedas / unidades | Conversión monetaria antes de agregar | Prueba USD/EUR; Float conserva unidad original |
| CSV / Excel | Exportación del filtro completo | Prueba con límite visible menor al resultado; fórmulas desactivadas |
| PNG | Gráfico o representación de tarjeta/lista | Descarga verificada en navegador |
| PDF | Gráfico más resultados tabulados | QWeb y descarga verificados |
| Transferencia | JSON de tablero o elemento y dependencias | Prueba de ida/vuelta con datasets y KPI relacionados |
| Archivos | CSV/XLSX, asignación de columnas y reemplazo | Prueba de sincronización CSV |
| Colaboración | Hilo y conversación privada en Discuss | Prueba de revocación de audiencia |
| Actualización | Bus al cambiar fuentes, con debounce; sondeo | Evento sin valores de negocio; navegador conectado al bus |
| Plantillas | Ventas/CRM/contabilidad/inventario/POS propias | Requieren aplicación fuente y adaptación al negocio |
| IA de creación | Modelo/palabras clave, propuesta revisable | Contrato Ollama y ausencia de datos en prompt de generación probados |
| IA explicativa | Resultados visibles del indicador | Implementada; requiere servicio/modelo configurados |

## Alcance que no se debe presentar como certificado

- Se probó inferencia real con LM Studio y Qwen 3.5 4B para un caso pequeño; no se afirma igualdad con la IA comercial ni comprensión universal. Las nuevas recetas explícitas no se presentan como inferencia.
- Se verificó Community 18 en Windows. La compatibilidad 19, futuras versiones, Enterprise y Odoo.sh sigue requiriendo entornos y pruebas propios.
- Los gráficos propios representan las mismas categorías funcionales con diseño y cartografía propios; no se afirma equivalencia visual exacta con el producto comercial.
- La playlist mezcla el producto base y extensiones Advance. Esta versión añade SQL sobre instantáneas con permisos, no SQL PostgreSQL directo. TV y conexiones externas continuas no están implementadas. Los ejemplos hoteleros, de margen/rotación y ahorro no están certificados de extremo a extremo; véase la matriz de videos.

Esta auditoría no declara “100 % idéntico”. Registra las equivalencias funcionales realizadas y las diferencias que todavía necesitan validación o una especificación adicional.
