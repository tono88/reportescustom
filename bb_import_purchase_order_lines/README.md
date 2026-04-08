# BB Import Purchase Order Lines

Módulo para **Odoo 18 Community** que agrega un botón en la orden de compra/RFQ para importar líneas desde **CSV** o **XLSX**.

## Qué hace

- Agrega el botón **Importar líneas** en la vista de compras.
- Abre un asistente para cargar el archivo.
- Permite buscar productos por:
  - referencia interna
  - código de barras
  - nombre
- Importa columnas base:
  - Producto
  - Descripción
  - Cantidad
  - UDM
  - Precio Unitario
  - Impuestos
  - Fecha de entrega
- Si el archivo tiene encabezados, acepta columnas extra usando el **nombre técnico** del campo de `purchase.order.line`.
- Muestra un resumen con líneas creadas y filas omitidas.
- Publica el resultado en el chatter de la orden de compra.

## Formatos soportados

- `.csv`
- `.xlsx`

## Requisito adicional

Instalar la librería de Python:

```bash
pip install openpyxl
```

## Instalación

1. Copia la carpeta `bb_import_purchase_order_lines` dentro de tu ruta de addons.
2. Reinicia Odoo.
3. Actualiza la lista de aplicaciones.
4. Instala el módulo **BB Import Purchase Order Lines**.
5. Asigna al usuario el grupo **Importar líneas de orden de compra** si hace falta.

## Uso

1. Ve a **Compras > Solicitudes de cotización**.
2. Abre una RFQ en borrador.
3. Haz clic en **Importar líneas**.
4. Adjunta el archivo CSV o XLSX.
5. Elige si el archivo tiene encabezados y el tipo de búsqueda de producto.
6. Importa.

## Plantilla base sugerida

```text
Producto,Descripción,Cantidad,UDM,Precio Unitario,Impuestos,Fecha de entrega
BLOCK-15,Block 15x20x40,1000,Unidad,4.50,IVA Compras,2026-04-07
```

## Nota

El soporte de campos extra funciona mejor cuando el encabezado usa el nombre técnico exacto del campo en `purchase.order.line`.
