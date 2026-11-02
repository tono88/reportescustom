# Tecnodyne Dashboards — Odoo 18 Community

Implementación original LGPL-3. Primera versión funcional, no paridad completa con Dashboard Ninja. Solo depende de `web`; no requiere Enterprise, OCA ni servicios externos. No contiene código, imágenes ni estilos de Ksolves.

## Instalación y uso

1. Añadir el directorio que contiene `tecnodyne_dashboard` al `addons_path` de Odoo 18. Reiniciar Odoo y actualizar la lista de aplicaciones.
2. Instalar **Tecnodyne Dashboards**. Asignar al configurador el grupo **Tecnodyne Dashboard Designer** y a los lectores **Tecnodyne Dashboard Viewer**.
3. Abrir Tecnodyne → Dashboards. Crear un tablero para Bloquera y otro para Ferretería, seleccionando su empresa. Los grupos de audiencia vacíos permiten acceso a todos los lectores del módulo que tengan esa empresa activa.
4. Agregar indicadores: modelo, tipo, agregación y medida numérica si no es conteo; escoger campo de agrupación para gráficos/tablas. Guardar y abrir el tablero.
5. Dominio JSON: `[["state", "=", "sale"]]`. Valores dinámicos: `[["user_id", "=", "$uid"]]` y `[["company_id", "=", "$company"]]`. No se ejecutan expresiones Python.
6. Elegir un campo fecha en cada indicador para activar el filtro global sobre ese indicador. CSV exporta los grupos mostrados, sujeto al límite configurado; no es una descarga completa de registros.
7. Importar/exportar configuración desde Tecnodyne → Import / Export. Copiar el JSON. La importación crea un tablero nuevo en la empresa activa, sin copiar permisos de audiencia ni datos. Los modelos/campos deben existir en el destino.

El duplicado estándar de Odoo copia el tablero y sus indicadores. La secuencia configura el orden. Los gráficos incluyen una tabla accesible y permiten abrir registros al pulsar un grupo.

## Seguridad y semántica

- Todas las consultas utilizan el usuario actual, sus ACL y reglas de registro; nunca `sudo` ni SQL libre. La audiencia y empresa se controlan también en el servidor.
- Cada tablero consulta una empresa autorizada y activa, con contexto de empresa acotado. En modelos con `company_id`, se excluyen registros compartidos sin empresa para evitar mezclas inadvertidas. En modelos sin empresa se conservan sus reglas nativas: un tablero no convierte esos modelos en datos exclusivos de una empresa.
- Los diseñadores configuran consultas; también necesitan permisos de lectura sobre las fuentes. Elegir un modelo no concede acceso a sus datos. Un indicador no autorizado provoca un error del tablero completo, sin conservar resultados anteriores.
- `unit` es una etiqueta, no conversión monetaria. Para dinero usar campos normalizados a moneda de compañía (por ejemplo saldo contable); no sumar importes con monedas distintas.
- Los filtros fecha son inclusivos. Los indicadores sin campo fecha no responden al rango. Las agrupaciones se ejecutan por ORM y el límite máximo es 200 grupos; una categoría truncada no es un total general.
- Actualización opcional por sondeo a 30/60/300 segundos; no equivale a bus de eventos ni streaming. Cada refresco vuelve a comprobar permisos.

## Compatibilidad

La versión distribuida tiene manifiesto **18.0**. Para 19 y siguientes se debe mantener una rama por versión, adaptar APIs ORM/OWL, ejecutar pruebas de instalación/seguridad y validar interfaz. No cambiar solamente el número de manifiesto. La ausencia de Enterprise reduce dependencias, no garantiza compatibilidad futura.

## Validación

`tests/test_dashboard.py`: conteo y detalle por empresa, bloqueo de otra empresa, lector sin escritura, ACL de origen, audiencia, conteo agrupado, dominio como datos e ida/vuelta JSON. Ejecutar en una **base de pruebas** con `--test-enable --test-tags /tecnodyne_dashboard --stop-after-init`.

Consultar [investigación y hoja de ruta](docs/INVESTIGACION.md) para alcance, fuentes y evolución.
