# Importación sin reiniciar: solo PDF de cheques personales

Este paquete es una alternativa de **solo datos XML**, para el menú
**Aplicaciones → Importar módulo** de Odoo 18 Community. No instala modelos,
métodos Python, campos nuevos, servicios, bibliotecas JavaScript ni conexión USB.
Requiere que `l10n_gt_check_printing2` y su dependencia `account_check_printing`
ya estén instalados y funcionando. No importar el ZIP de la extensión LX-350
completa desde esa pantalla.

## Instalación

1. Usar exclusivamente `l10n_gt_check_printing2_pdf_live-18.0.1.0.1.zip`.
2. En **Importar módulo**, seleccionar ese ZIP. Dejar **Forzar inicio** y
   **Cargar datos de prueba** desmarcados. Instalar.
3. Recargar el navegador y abrir un pago saliente mediante cheque.

Para actualizar la versión importada anterior, importar este ZIP con el mismo
nombre técnico, sin desinstalar y con **Forzar inicio** desmarcado. Cerrar el PDF
anterior y descargar uno nuevo desde el pago. El importador actualiza los reportes
y vistas de este módulo; conservar antes una copia de las posiciones si se habían
editado manualmente en QWeb.

No requiere reiniciar el servicio porque solo agrega reportes y vistas a los
modelos existentes. Tampoco cambia los reportes ni el voucher actuales, los
diarios, el diseño elegido en ajustes, los números o el estado de los pagos.
No se han ejecutado la importación ni las pruebas en tu base de producción.

## Uso sin alterar la numeración

1. Usar el flujo habitual de **Imprimir cheque** para confirmar el pago y asignar
   el número preimpreso. Si genera el PDF anterior, no imprimir esa copia.
2. Al volver al pago con número asignado y estado En proceso o Pagado aparecerán
   dos botones: **PDF Banrural personal** y **PDF G&T personal**.
3. Elegir el botón del banco al que realmente corresponde el diario/cuenta del
   pago. Ambos botones están disponibles: esta versión no tiene los campos ni
   métodos Python de la versión completa para seleccionar el banco automáticamente.
4. Revisar el PDF antes de imprimir. Si muestra **NO ES UN CHEQUE VÁLIDO PARA
   IMPRIMIR**, revisar el pago y no imprimir esa página sobre un cheque.
5. Imprimir manualmente desde el visor de PDF, al 100 % / tamaño real, sin
   «ajustar a página». Mantener el voucher como reporte independiente.

Estos botones solo generan PDF de un pago ya numerado. No ejecutan otra vez el
asistente, no asignan números y no marcan ni desmarcan pagos como enviados. Una
segunda descarga puede ser otra copia: comprobar cola y papel antes de imprimir.
No hay impresión directa QZ, calibración por campos del diario ni botón de prueba
con datos ficticios. Esas funciones requieren la extensión de servidor y una
ventana de mantenimiento.

## Tamaño y posiciones

Ambos cuerpos de cheque se consideran personales, nominalmente
**165.10 × 69.85 mm**. Los campos nativos de Odoo 18 para el tamaño de papel son
enteros; el lienzo PDF es **165 × 70 mm**. Esto evita el error al cargar los
decimales del ZIP anterior. Las coordenadas iniciales se estimaron de las fotos
y deben calibrarse en papel común antes de usar originales.

Desde 18.0.1.0.1 se utiliza **96 DPI**, con `data-report-dpi="96"` en el HTML para
evitar el factor adicional `96 / dpi` del generador de Odoo. La posición relativa,
el tamaño y la fuente van directamente en cada `.article`, porque Odoo extrae
esos bloques a su layout mínimo y no conserva el estilo del encabezado original.
El monto termina a 160 mm en sus coordenadas de diseño, dejando 5 mm de margen.
Se usa Courier New con tamaños de letra enteros para mantener espaciado legible
en el generador PDF y una tipografía apropiada para impresión matricial.

La Epson LX-350 especifica un mínimo de 100 × 100 mm para hojas sueltas estándar;
debe validarse la alimentación compatible para un cheque suelto de 69.85 mm.
El tamaño del PDF no soluciona la limitación mecánica. Si el soporte/formulario
es mayor, el papel del reporte también debe adaptarse al formulario completo.

Para ajustar las posiciones sin código de servidor, en modo desarrollador:
**Ajustes → Técnico → Interfaz de usuario → Vistas**, localizar la vista QWeb
con identificador `l10n_gt_check_printing2_pdf_live.check_document`.
En su diccionario `profile` hay un bloque `banrural` y otro `gyt`:

- `offset_x`: negativo mueve a la izquierda; positivo a la derecha.
- `offset_y`: positivo mueve hacia abajo; negativo hacia arriba.
- `date`, `amount`, `payee`, `words`: tuplas `(izquierda, arriba, ancho)` en mm.
- `city`: lugar de emisión, PALÍN inicialmente.

Esas posiciones son por banco y se comparten entre empresas en esta variante.
Guardar una copia de la arquitectura antes de editar y probar el PDF después.
No reimportar el paquete sobre ajustes manuales sin guardar una copia, porque
la importación puede reemplazar esas vistas. Para calibración por diario y
empresa, utilizar la versión completa cuando se pueda reiniciar.

## Validación y alcance

Se verifican estructura XML, tamaños enteros, referencias internas, ausencia de
Python ejecutable en el paquete y evaluación de las expresiones del reporte con
datos simulados. Se reprodujo el recorte con wkhtmltopdf 0.12.6 a 90 DPI y el zoom
de Odoo, y se comprobó el PDF corregido a 96 DPI para ambos bancos. La importación
real y la envoltura completa de la instalación Odoo del cliente no se han ejecutado aquí.
Las imágenes con datos bancarios y firmas no se incluyen en el paquete.

Fuentes:

- [Odoo 18: tamaños de papel](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/report_paperformat.py).
- [Odoo 18: importación de módulos de datos](https://github.com/odoo/odoo/blob/18.0/addons/base_import_module/models/ir_module.py).
