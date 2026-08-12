# Saldos por Fecha de Factura - Estado Actual (Odoo 18 Community)

## Objetivo
Permite seleccionar un rango de **fecha de factura** y mostrar el **saldo actual** de esos documentos.

Ejemplo: una factura emitida en junio y pagada/conciliada en agosto aparecerá en el reporte de junio con:
- Estado: Pagado
- Saldo actual: 0
- Pagado actual: total de la factura

Esto es deliberadamente distinto de un Aged Receivable/Payable histórico al 30 de junio.

## Menús
Facturación / Contabilidad -> Informes -> Informes de terceros:
- Saldos actuales de clientes
- Saldos actuales de proveedores

## Filtros
- Compañía
- Fecha de factura desde/hasta
- Clientes/proveedores opcionales
- Incluir documentos ya pagados (activo por defecto)

## Salida
- PDF agrupado por tercero
- Botón "Ver documentos" para abrir las facturas/facturas de proveedor incluidas

## Dependencias
Solo `account` de Odoo 18 Community.

## Instalación en Windows 11
1. Descomprimir/copiar la carpeta `current_invoice_balance_report` dentro de una ruta incluida en `addons_path`.
2. Reiniciar el servicio/servidor Odoo.
3. Activar modo desarrollador.
4. Apps -> Actualizar lista de aplicaciones.
5. Buscar "Saldos por Fecha de Factura - Estado Actual" e instalar.

## Nota contable
El saldo cambia únicamente cuando los pagos/notas de crédito están correctamente **conciliados** contra la factura. Un pago registrado pero no conciliado no reduce el `amount_residual` de la factura.
