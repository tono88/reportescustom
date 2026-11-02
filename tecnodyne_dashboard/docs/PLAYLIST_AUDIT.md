# Revisión de la playlist y corrección funcional — 18.0.3.0.0

Revisión del 2 de noviembre de 2026 de la [playlist facilitada](https://www.youtube.com/playlist?list=PLhMLMIKkNp0DFDBzS84ggUl0jKfJFuad3). Se recuperaron los once títulos y descripciones públicas de YouTube. No se obtuvo una transcripción ni se reprodujeron íntegramente los videos; esta matriz no certifica cada interacción mostrada en pantalla. No se utilizó código propietario.

## Error corregido

La propuesta anterior aceptaba un conteo técnicamente válido aunque no respondiera a «categorías más vendidas por mes». Además, seleccionar `product.category` describe el catálogo, no las operaciones vendidas. Las pruebas previas de formato JSON no demostraban que el análisis fuera correcto.

Ahora **Origen automático** resuelve recetas explícitas. Para esa petición genera dos barras independientes: Ventas (`sale.report`) y POS (`report.pos.order`), suma unidades o importe sin impuestos, categoría y mes. Ventas incluye pedidos confirmados; POS incluye pagados, contabilizados o facturados. Excluye borradores/cancelados. El Top N se calcula dentro de cada mes. Las unidades corresponden a la unidad base del producto; sumar unidades incompatibles no representa una magnitud homogénea. Los reembolsos se reflejan como cantidades/importes negativos cuando la fuente los contiene. Las categorías son las actuales del producto, no una reconstrucción histórica.

La propuesta se invalida al cambiar la petición o los parámetros y se vuelve a validar al aplicarla. Se rechaza un conteo no solicitado. Estas recetas usan reglas de negocio comprobables; no se presentan como inferencia de LM Studio. Las consultas genéricas siguen usando la IA configurada y requieren un modelo apropiado y revisión humana.

## Matriz de los once videos

| Referencia | Capacidad descrita | Estado en Tecnodyne y límites |
|---|---|---|
| [Generación de dashboards con IA](https://www.youtube.com/watch?v=oyoBYcvimSQ) | Tableros completos, modelo/palabras clave y opciones predefinidas | Generación y aplicación revisada; nuevos análisis predefinidos de categorías, productos, tendencia mensual y contabilidad. Consultas abiertas dependen de la calidad del modelo. No se certifica interpretación universal. |
| [Conversaciones internas](https://www.youtube.com/watch?v=VC8MpF8TweA) | Conversaciones por gráfico y bandeja unificada | Conversación privada por indicador, Discuss y chatter; se verifican audiencias. Usa la bandeja nativa de Odoo, no una copia de la interfaz comercial. |
| [Mover o duplicar](https://www.youtube.com/watch?v=7IT5oboir4M) | Mover/copiar entre tableros | Asistente con permisos y acceso directo desde la tarjeta en edición. |
| [Edición del diseño](https://www.youtube.com/watch?v=hi7WBDeqovQ) | Arrastrar, soltar y redimensionar | Reordenamiento, tamaño por controles y nuevo tirador con puntero. Diseños privados persistentes. |
| [CSV y Excel](https://www.youtube.com/watch?v=SUrWTw5umiI) | Datos externos y gráficos dinámicos | Importación/reemplazo manual, columnas mapeadas y conservación de todas las columnas originales en JSON, con tipos configurables. Se pueden consultar con `json_extract` desde SQL. No vigila archivos externos automáticamente. |
| [Consultas personalizadas](https://www.youtube.com/watch?v=f9IgKvqCpSs) | SQL, varios modelos, usuario/empresa dinámicos | Nuevo SELECT/WITH, JOIN, ventanas y parámetros. Se ejecuta en SQLite aislado sobre instantáneas leídas con permisos Odoo; no accede directamente a PostgreSQL ni admite cualquier sintaxis PostgreSQL. Hasta cinco fuentes, 10.000 filas por fuente/20.000 total; exceder límites produce error, no resultados parciales. |
| [Drill down](https://www.youtube.com/watch?v=UlIObcl7P3E) | Cliente, vendedor, fechas, registros | Jerarquía ordenada configurable y navegación a registros ORM. SQL navega solo si devuelve un identificador autorizado y su alias; no infiere el detalle de un agregado SQL arbitrario. |
| [Área, embudo, polar y tareas](https://www.youtube.com/watch?v=xnV191hL_f8) | Tipos de indicador, fechas, dominios, importación | Tipos implementados, filtros temporales y dominios, tareas persistentes. Diseño propio; no se afirma equivalencia visual exacta. |
| [Retail](https://www.youtube.com/watch?v=GZXH_Da3FwE) | Tendencia, productos principales, existencias, rotación y margen | Nuevas recetas de tendencia/productos/categorías, separadas por canal. Existencias, rotación y margen pueden configurarse con modelos/consultas; **no hay recetas automáticas verificadas para esas tres últimas métricas**. Valorar stock o margen requiere acordar fecha, coste y movimientos. |
| [Hotelería](https://www.youtube.com/watch?v=reWjW2n8Ros) | Ocupación, ADR, RevPAR, limpieza y estancia | **Pendiente de fuente hotelera y recetas probadas**. Sales/POS no contienen habitaciones disponibles, noches ocupadas ni estados de limpieza. El motor de consultas/razones puede representarlos con una fuente adecuada; eso no equivale a tenerlos implementados de extremo a extremo. |
| [Finanzas](https://www.youtube.com/watch?v=f-6cZxR9VBA) | Resultados, efectivo por contacto, ahorro, gastos y proveedores | Recetas de resultado contable, movimiento neto de caja, saldo de caja/bancos, gastos y residual actual de proveedores. Solo asientos publicados. Saldo mensual incluye apertura y meses sin movimientos; residual actual no reconstruye antigüedad histórica. **Ahorro y previsiones financieras no tienen receta verificada**. No sustituye conciliación bancaria ni estados financieros reglamentarios. |

## Uso del caso solicitado

1. Actualizar el módulo a **18.0.3.0.0** y recargar el navegador.
2. Abrir **Generar con IA**; escoger **Categorías más vendidas por mes** y **Origen automático**.
3. Elegir **Ventas y POS por separado**, cantidad neta (o importe sin impuestos), máximo al menos dos indicadores y el Top deseado.
4. Generar una propuesta nueva, revisar y aplicar. Elegir el rango de fechas del tablero.

Los indicadores antiguos de conteo no se borran automáticamente. Una propuesta nueva añade indicadores al tablero seleccionado. Comparar primero con los informes nativos de Ventas y POS de la misma empresa, período y estados. No se ha conciliado con la base de negocio del usuario.

## Consultas propias

En el indicador seleccionar modo SQL, crear fuentes con alias, modelo, campos, dominio y fecha. Los campos many2one añaden una columna `campo__name`. Parámetros: `:uid`, `:company`, `:date_from`, `:date_to`; también se sustituyen `%UID` y `%MYCOMPANY`. Devolver columnas únicas `label` y `value`, opcionalmente `series`, `value2`, `record_id`, `source_alias`, `lat`, `lon`. Las columnas originales de archivos están en `raw_json`, por ejemplo `json_extract(raw_json,'$.Unidades')`.

Las fuentes conservan ACL, reglas, restricciones de campos y empresa del tablero. Los registros sin empresa se incluyen únicamente al marcar la opción correspondiente. Solo se eleva la lectura de metadatos configurados, nunca los datos de negocio. Las consultas tienen límites de tiempo, filas y tamaño, sin escrituras ni extensiones. La transferencia JSON esquema 3 conserva fuentes, tipos, datos importados, alcance temporal y orden de detalle; admite esquemas 1 y 2.

**No se declara paridad total con la playlist.** Esta entrega corrige el caso reproducido y añade capacidades generales que faltaban; la tabla identifica los ejemplos de dominio aún incompletos. Solo Odoo 18 Community ha sido probado; 19 y posteriores requieren port y validación propios.
