POS Internal Correlative (Odoo 18)
----------------------------------
- Genera un correlativo interno (A-00001, A-00002, ...) al crear cada `pos.order`.
- Copia ese valor a las facturas como campo calculado `x_pos_internal_correlative`.
- Añade el campo a las vistas (árbol, búsqueda y formulario) de POS y Facturas.
- Muestra el correlativo en el recibo del POS (si no está, cae al nombre de orden).

Si ya existen órdenes sin correlativo, puedes rellenarlo ejecutando desde el `Modo Desarrollador`:
Acciones -> Ejecutar `server action` (crear una si hace falta) con:

    env['pos.order'].search([('internal_correlative','=',False)]).sudo()._write({'internal_correlative': False})

Y luego, para los que quedaron a False, guarda manualmente o crea una acción python
que llame a `create([])` para disparar la secuencia en nuevos registros.
