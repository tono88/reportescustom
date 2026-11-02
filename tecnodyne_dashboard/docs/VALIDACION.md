# Validación de la primera entrega

Fecha: 2 de noviembre de 2026. Entorno: Windows, Odoo Community 18.0-20250924 instalado localmente; PostgreSQL local.

- Instalación y actualización reales en base nueva aislada `tecnodyne_dashboard_test_20261102`; ninguna instalación en la base de negocio.
- Resultado final Odoo: **9 pruebas, 0 fallos, 0 errores**. Incluye dominios, ACL del origen, audiencia, aislamiento empresarial, bloqueo de escritura a lectores, agrupación, transferencia JSON y límites horarios de Guatemala.
- Ambas plantillas se compilaron con el OWL incluido en esa instalación.
- Montaje de los cinco tipos de indicador en DOM de prueba con servicios y Chart simulados: cinco tarjetas y tres ciclos de gráficos. Esta prueba valida estructura y ciclo de componentes; no valida el dibujo real de Chart.js.
- JavaScript pasó la comprobación sintáctica de Node. SCSS compiló con el compilador Sass incluido en Odoo.

Pendiente antes de producción: QA visual en navegador con Chart.js real, validación de importes contra datos del negocio, pruebas de volumen y confirmación de permisos de los usuarios finales. Odoo 19 y posteriores no se probaron.

Para repetir las pruebas de backend: iniciar Odoo con el directorio padre del módulo en `addons_path`, base de pruebas seleccionada, directorio de datos escribible y parámetros `-i tecnodyne_dashboard --test-enable --test-tags /tecnodyne_dashboard --stop-after-init`. Para una base ya instalada usar `-u`.
