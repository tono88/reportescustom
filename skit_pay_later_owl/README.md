# SKIT Pay Later (OWL) — Odoo 18 Community

**Qué hace:** añade un flujo ligero de **'Pagar después'** al POS sin jQuery/Bootstrap, 100% OWL/ESM.
- Botón **Pagar después** en `PaymentScreen`: valida cliente y guarda la orden en `localStorage`.
- Botón **Recuperar Pay Later** en `ProductScreen`: permite seleccionar y cargar una orden guardada para cobrarla luego.

> **Importante (límites CE):** Este módulo **no crea deuda contable ni factura**. Guarda la orden para cobrarla más tarde en el POS. Para deuda real (cuentas por cobrar) y facturación automática desde POS en CE, se requiere desarrollo backend adicional o módulos de terceros compatibles con Odoo 18.

## Instalación
1. Copiar la carpeta `skit_pay_later_owl` al `addons_path`.
2. Apps → Actualizar lista → Instalar **SKIT Pay Later (OWL, POS 18)**.
3. Refrescar caché del navegador (Ctrl+F5).

## Uso
- En cobro, pulse **Pagar después** → la orden se guarda (requiere **cliente**).
- Más tarde, en la pantalla de productos, pulse **Recuperar Pay Later** → elija la orden → será cargada y podrá **cobrarla normalmente**.

## Compatibilidad
- Odoo **18.0 Community**.
- No usa jQuery, Bootstrap ni `odoo.define` legado.
- Solo front‑end; no altera `pos.order` en backend.

## Extensión a crédito real (roadmap)
- Añadir campo `x_pay_later` en `pos.order` y endpoint para aceptar órdenes sin `paymentlines` (estado `to_pay`).
- Proceso de cierre que genere asientos/factura al consolidar pagos diferidos.
- UI para abonar/conciliar pagos parciales desde POS.