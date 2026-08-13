# Saldos por Fecha - Estado Actual (Odoo 18 Community)

Reporte de saldos para clientes y proveedores.

## Clientes

Permite seleccionar:
- Solo facturados: usa `account.move.invoice_date` para el periodo y el residual actual de la factura.
- Solo no facturados: usa pedidos `pos.order` sin factura y la fecha del pedido POS.
- Facturados y no facturados: combina ambos orígenes.

El reporte conserva la lógica solicitada: una factura de junio pagada/conciliada en agosto aparece con saldo actual cero.

Para los pedidos POS no facturados se reutiliza la lógica del reporte `pos_multi_warehouse_sales_report`: se excluyen pedidos de reembolso y sus órdenes origen reembolsadas.

## Columnas PDF/XLSX

1. Fecha factura
2. Cliente / Proveedor
3. Orden POS
4. DTE FEL
5. Total factura
6. Total pagado
7. Saldo pendiente

El correlativo POS usa `internal_correlative` cuando el módulo `pos_internal_correlative` está instalado; si no, usa el nombre estándar del pedido.
El DTE FEL usa `numero_fel` cuando existe y tiene fallbacks para otros nombres habituales.

## Proveedores

Solo usa facturas de proveedor. El saldo se calcula con el residual actual, incluyendo pagos posteriores al periodo.

## Dependencias

- account
- point_of_sale


## Versión 18.0.1.2.0 - fecha inicial automática

Se agregó el check **Usar fecha más antigua automáticamente**.

- Al activarlo, `Fecha desde` se calcula automáticamente y queda de solo lectura.
- El usuario únicamente necesita elegir `Fecha hasta`.
- La fecha mínima se recalcula al cambiar compañía, tipo de reporte, modo Facturados/No facturados, terceros, inclusión de pagados o fecha final.
- En **Solo facturados** toma la factura/nota de crédito fiscal más antigua que cumpla los filtros.
- En **Solo no facturados** toma el pedido POS no facturado más antiguo válido, excluyendo reembolsos y órdenes origen reembolsadas.
- En **Facturados y no facturados** toma la menor fecha entre ambos orígenes.
- Para proveedores aplica sobre las facturas de proveedor.


## 18.0.1.3.0
- Corrige el saldo de pedidos POS no facturados.
- Replica el criterio individual de `pos_sales_summary_report`: efectivo se considera pagado/contado y cualquier otro método se considera crédito/saldo pendiente.
- Ya no depende de `pos.order.amount_paid` para calcular el saldo de no facturados, porque Odoo puede marcar como pagado el total técnico del pedido aunque exista una parte registrada como crédito.
