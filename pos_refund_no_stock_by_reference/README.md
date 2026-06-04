# POS Refund No Stock by Reference

Módulo para Odoo 18 que crea reembolsos POS pagados desde un Excel de una columna, sin generar movimientos de inventario.

## Qué hace

- Lee un archivo `.xlsx`.
- Toma las referencias desde la primera columna.
- Busca órdenes por `pos_reference` y como respaldo por `name`.
- Crea una nueva orden POS de reembolso con cantidades negativas.
- Crea pagos negativos para dejar el reembolso pagado.
- Marca el reembolso como `paid` sin llamar a `action_pos_order_paid()`.
- Marca la orden con `no_stock_refund=True`.
- Evita pickings mediante override de `_create_order_picking()` para esas órdenes.
- No cancela ni modifica la orden original.

## Requisito Python

```bash
pip install openpyxl
```

## Uso

1. Instalar el módulo.
2. Entrar a **Punto de Venta > Reembolsar POS sin inventario**.
3. Cargar Excel `.xlsx` con la referencia POS en la primera columna.
4. Opcionalmente elegir una sesión POS abierta destino.
5. Ejecutar **Crear y pagar reembolsos**.

## Nota importante

Este módulo no genera devolución de inventario. Contablemente crea pagos negativos en POS. Si se requiere una nota de crédito fiscal/FEL, eso debe manejarse con un flujo adicional.
