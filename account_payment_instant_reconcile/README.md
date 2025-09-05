# Instant Reconcile on Payment (Community)

**Objetivo**: En Odoo 18 Community, algunos despliegues no incluyen el ajuste estándar de "Publicar en/Conciliar en banco".
Este módulo añade una **opción por diario** para **reconciliar automáticamente** los pagos al momento de **validarlos**, de modo que
las facturas queden **Pagadas** sin esperar conciliación bancaria.

## Cómo funciona
- Nuevo campo en Diario de Banco: **Reconciliar pago al validar** (`instant_reconcile_on_post`, activo por defecto).
- Al validar un pago, el módulo busca líneas abiertas **por cobrar/pagar** del mismo partner y **reconcilia** contra el pago.
- Soporta **parciales** si los importes no coinciden exactamente (usa la reconciliación estándar de Odoo).

## Instalación
1. Copiar la carpeta `account_payment_instant_reconcile` dentro de tu ruta de addons.
2. Actualizar la lista de apps y **instalar** el módulo.
3. En cada Diario (Banco/Caja) verifica el toggle en **Ajustes avanzados**.

## Notas
- Este módulo **no** modifica asientos para usar cuentas de liquidez directamente; solo realiza la **reconciliación** inmediata.
- Si usas extractos bancarios y conciliación automática por modelos, puedes **desactivar** el toggle en diarios donde no lo desees.