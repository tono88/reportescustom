# Importación sin reiniciar: solo PDF de cheques personales

Este paquete es una alternativa de **solo datos XML**, para el menú
**Aplicaciones → Importar módulo** de Odoo 18 Community. No instala modelos,
métodos Python, campos nuevos, servicios, bibliotecas JavaScript ni conexión USB.
Requiere que `l10n_gt_check_printing2` y su dependencia `account_check_printing`
ya estén instalados y funcionando. No importar el ZIP de la extensión LX-350
completa desde esa pantalla.

## Instalación

1. Usar exclusivamente `l10n_gt_check_printing2_pdf_live-18.0.1.0.5.zip`.
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
   dos botones: **PDF Banrural personal v1.0.5** y **PDF G&T personal v1.0.5**.
3. Elegir el botón del banco al que realmente corresponde el diario/cuenta del
   pago. Ambos botones están disponibles: esta versión no tiene los campos ni
   métodos Python de la versión completa para seleccionar el banco automáticamente.
4. Revisar el PDF antes de imprimir. Si muestra **NO ES UN CHEQUE VÁLIDO PARA
   IMPRIMIR**, revisar el pago y no imprimir esa página sobre un cheque.
5. En el visor y el controlador Epson seleccionar **Carta / Letter**, orientación
   vertical y **100 % / tamaño real**, sin «ajustar a página». El cheque se coloca
   contra la guía izquierda en 0; las coordenadas parten de esa referencia.
   Mantener el voucher como reporte independiente.

Estos botones solo generan PDF de un pago ya numerado. No ejecutan otra vez el
asistente, no asignan números y no marcan ni desmarcan pagos como enviados. Una
segunda descarga puede ser otra copia: comprobar cola y papel antes de imprimir.
No hay impresión directa QZ, calibración por campos del diario ni botón de prueba
con datos ficticios. Esas funciones requieren la extensión de servidor y una
ventana de mantenimiento.

## Tamaño y posiciones

Ambos cuerpos de cheque se consideran personales, nominalmente
**165.10 × 69.85 mm**. Desde 18.0.1.0.2 se utiliza un **lienzo PDF Carta**
(215.9 × 279.4 mm) y todos los datos quedan en el área del cheque, arriba a la
izquierda. El PDF se verá como una hoja Carta con el resto en blanco: es intencional.
Al imprimir un PDF pequeño de 165.1 mm sobre Carta, un visor puede agregar
25.4 mm a cada lado para centrarlo; con PDF y controlador ambos en Carta se
elimina esa diferencia de tamaño. Esto presupone que Carta es el formato elegido
en Windows: si se usa otro tamaño, debe coincidir con el PDF.

No se estima un corrimiento adicional a partir del video. Se fija el origen en
la izquierda en lugar de adivinar una compensación. Las posiciones iniciales
de los campos respecto a ese origen son:

| Campo | Banrural: izquierda / arriba / ancho (mm) | G&T: izquierda / arriba / ancho (mm) |
|---|---|---|
| Fecha | 18 / 24 / 110 | 24 / 25 / 100 |
| Monto | 137 / 24 / 25 | 137 / 25 / 25 |
| Beneficiario | 18 / 31 / 144 | 24 / 33 / 138 |
| Letras | 18 / 38 / 144 | 24 / 41 / 138 |

Estas coordenadas se estimaron de las fotos y deben verificarse con una prueba.
Los parámetros `offset_x` y `offset_y` siguen disponibles en QWeb para compensar
un desplazamiento constante después de fijar el papel, sin cambiar numeración.

Desde 18.0.1.0.1 se utiliza **96 DPI**, con `data-report-dpi="96"` en el HTML para
evitar el factor adicional `96 / dpi` del generador de Odoo. La posición relativa,
el tamaño y la fuente van directamente en cada `.article`, porque Odoo extrae
esos bloques a su layout mínimo y no conserva el estilo del encabezado original.
Desde 18.0.1.0.4, en Banrural el monto empieza en **137 mm**, alineado a la
izquierda dentro del espacio que sigue al «Q.» preimpreso, y tiene 25 mm
disponibles (hasta 162 mm). En la fotografía, el inicio del monto impreso se
estima a 97 mm del borde izquierdo: la posición objetivo equivale a unos
40 mm a la derecha respecto a esa impresión. La versión 18.0.1.0.3 ya usaba
135 mm, por lo que este cambio de plantilla agrega 2 mm; no se suman 40 mm
a la coordenada anterior. La estimación depende de la perspectiva de la foto
y se confirma con una prueba a tamaño real. Desde 18.0.1.0.5, G&T también usa
inicio fijo en 137 mm y alineación izquierda en un campo de 25 mm; el inicio
ya no depende de la cantidad de dígitos.

Desde 18.0.1.0.3, fecha, beneficiario y monto usan hasta **12 pt**, y el importe
en letras hasta **11 pt**. Desde 18.0.1.0.5 se cambia Courier New por
**Arial negrita**, con alternativa Liberation Sans y tamaños enteros. El cálculo
de ancho distingue dígitos, signos, letras estrechas y letras anchas. Los textos
largos se reducen hasta 9 pt; si no caben se genera el aviso de revisión en lugar de truncarlos. En QWeb,
`font_sizes` contiene los tamaños de cada campo y `min_font` el mínimo permitido.

## Impresión matricial y comprobación pendiente

El PDF no envía órdenes ESC/P ni selecciona por sí solo una fuente residente de
la Epson. El controlador de Windows participa en la conversión del documento.
Para probar la fidelidad del PDF, en las preferencias del controlador Epson:

- **Printer Font Setting: None (bit image printing)**, si aparece disponible,
  para evitar sustituir la fuente del PDF por fuentes residentes.
- **Graphic - Print Quality**: la resolución más alta disponible.
- **Print Speed: Standard**, si aparece disponible.
- Carta / Letter, vertical, tamaño real / 100 %, una página por hoja.

Estas opciones se basan en el manual oficial Epson; pueden variar con la versión
del controlador. No se cambian automáticamente al importar este módulo. La letra
en negrita busca mejorar el trazo, pero no certifica ni repara cinta o cabezal.

La nueva fotografía G&T muestra el monto aproximadamente a 98 mm del borde
izquierdo, mientras el PDF reproducido localmente lo sitúa cerca de 137 mm.
El usuario confirma que usó el botón G&T 1.0.4 y 100 %. Falta examinar el PDF
exacto descargado del servidor para distinguir generación, sustitución de fuente
y transformación al imprimir. No se añade una compensación arbitraria de 40 mm
al PDF: podría sacar el monto del cheque al corregir el controlador. La posición
física continúa pendiente de verificación. Los botones y nombres de descarga
incluyen v1.0.5 para identificar inequívocamente la nueva versión.

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
- [Epson LX-350: fuentes residentes, mapa de bits y calidad del controlador](https://files.support.epson.com/htmldocs/lx350_/lx350_ug/html/soft_4.htm).
