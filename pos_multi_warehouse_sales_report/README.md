# POS Multi Warehouse Sales Report

Módulo para Odoo 18 Community que agrega un reporte de ventas POS por almacén y producto.

## Dependencias

- point_of_sale
- stock
- account
- bi_pos_multi_warehouse

## Ruta del menú

Punto de venta → Órdenes → Ventas por almacén

## Filtros del asistente

- Fecha inicial
- Fecha final
- Compañías
- Cliente
- Almacén
- Facturación: todos, solo facturados o solo no facturados

## Campos principales del reporte

- Fecha de venta
- Compañía
- Almacén
- Producto
- Cantidad
- Precio unitario
- Descuento
- Subtotal sin impuesto
- Total con impuesto
- Cliente
- Orden POS
- Referencia/recibo
- Factura
- Sesión
- Punto de venta
- Cajero
- Estado POS

## Uso

1. Copiar la carpeta `pos_multi_warehouse_sales_report` en la ruta de addons personalizada.
2. Reiniciar Odoo.
3. Activar modo desarrollador.
4. Actualizar lista de aplicaciones.
5. Instalar `POS Multi Warehouse Sales Report`.
6. Ir a Punto de venta → Órdenes → Ventas por almacén.


## Fix 18.0.1.0.5
El menú se declara de forma estática bajo el XML ID oficial `point_of_sale.menu_point_of_sale`, que corresponde a Punto de venta / Órdenes en Odoo 18 Community.


## 18.0.1.0.9

- Excluye del reporte las órdenes POS cuya factura relacionada tenga una nota de crédito de cliente activa relacionada por `reversed_entry_id` / `reversal_move_ids`.
- No usa `payment_state` para decidir si una factura está revertida.


## 18.0.1.0.10
- Ajuste: solo excluye facturas con nota de crédito relacionada si la nota de crédito está publicada (`state = posted`). Las notas de crédito en borrador ya no sacan la factura del reporte.


## 18.0.1.0.11
- Usa fecha de factura para ventas facturadas.
- Las notas de crédito futuras ya no excluyen facturas de períodos anteriores.
- Solo se excluyen facturas con notas de crédito de cliente publicadas dentro del rango seleccionado.


## 18.0.1.0.12
- Se removió la exclusión de facturas originales por tener nota de crédito relacionada.
- Las facturas publicadas del período permanecen en el reporte aunque tengan nota de crédito.
- Se siguen excluyendo facturas canceladas, inexistentes y documentos tipo nota de crédito (`out_refund`) cuando vienen como factura enlazada de la orden POS.


## 18.0.1.0.13
- Agrega fallback para encontrar facturas por `account.move.ref = pos.order.name` cuando el pedido POS está facturado pero no tiene vínculo técnico `account_move`.
- El filtro Solo facturados ya no depende exclusivamente del campo `account_move` de la orden POS.
