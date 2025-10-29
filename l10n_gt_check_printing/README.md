# Guatemala - Check Printing (Community)

Este módulo añade diseños de **cheques** imprimibles para Guatemala en Odoo 18 Community.

## ¿Qué hace?
- Agrega 3 variantes de layout (talón arriba, medio y abajo).
- Se integra con *Ajustes de Facturación → Pagos de proveedor → Cheques → Diseño del cheque*.
- Usa unidades en **mm** y posiciones absolutas para coincidir con papelería física.
- Respeta márgenes superior/izquierdo configurables por compañía.

## Cómo usar
1. Instala el módulo.
2. Ve a **Facturación → Configuración → Ajustes** y activa *Cheques*.
3. Selecciona el *Diseño del cheque*: «Cheque GT - Top/Middle/Bottom».
4. Desde un **Pago de proveedor** con método *Cheque*, usa *Imprimir → Cheque Guatemala*.

## Personalización rápida
- Ajusta posiciones editando `reports/report_check_templates.xml`.
- Duplica el template y cambia `t-call` o estilos para bancos específicos (font/coord).

## Notas
- El reporte apunta al modelo `account.payment`. Si usas un flujo distinto,
  ajusta el `model` del `ir.actions.report`.