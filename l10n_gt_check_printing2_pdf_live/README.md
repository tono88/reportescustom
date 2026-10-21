# Importación sin reiniciar: solo PDF de cheques personales

Este paquete es una alternativa de **solo datos XML**, para el menú
**Aplicaciones → Importar módulo** de Odoo 18 Community. No instala modelos,
métodos Python, campos nuevos, servicios, bibliotecas JavaScript ni conexión USB.
Requiere que `l10n_gt_check_printing2` y su dependencia `account_check_printing`
ya estén instalados y funcionando. No importar el ZIP de la extensión LX-350
completa desde esa pantalla.

## Instalación

1. Usar exclusivamente `l10n_gt_check_printing2_pdf_live-18.0.1.0.10.zip`.
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
   dos botones: **PDF Banrural personal v1.0.10** y **PDF G&T personal v1.0.10**.
3. Elegir el botón del banco al que realmente corresponde el diario/cuenta del
   pago. Ambos botones están disponibles: esta versión no tiene los campos ni
   métodos Python de la versión completa para seleccionar el banco automáticamente.
4. Revisar el PDF antes de imprimir. Si muestra **NO ES UN CHEQUE VÁLIDO PARA
   IMPRIMIR**, revisar el pago y no imprimir esa página sobre un cheque.
5. En el visor y el controlador Epson seleccionar **Carta / Letter**, orientación
   vertical y **100 % / tamaño real**, sin «ajustar a página». Esta versión
   compensa 20 mm solo en el monto: conservar la misma colocación y configuración
   de la impresión anterior y comprobar primero en papel común.
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
(215.9 × 279.4 mm). Desde 18.0.1.0.7, el monto usa una compensación de impresora
y ocupa parte del lienzo Carta fuera del cuerpo nominal de 165.1 mm. La hoja
Carta representa las coordenadas de impresión, no el tamaño físico del cheque.
Al imprimir un PDF pequeño de 165.1 mm sobre Carta, un visor puede agregar
25.4 mm a cada lado para centrarlo; con PDF y controlador ambos en Carta se
elimina esa diferencia de tamaño. Esto presupone que Carta es el formato elegido
en Windows: si se usa otro tamaño, debe coincidir con el PDF.

Las posiciones base describen el cheque. `amount_shift_x = 20` se suma
exclusivamente al monto; `offset_x` y `offset_y` siguen siendo ajustes generales.
Las posiciones efectivas de la plantilla son:

| Campo | Banrural: izquierda / arriba / ancho (mm) | G&T: izquierda / arriba / ancho (mm) |
|---|---|---|
| Fecha | 18 / 24 / 110 | 24 / 25 / 100 |
| Monto, con compensación | 157 / 24 / 25 | 155 / 27 / 25 |
| Beneficiario | 18 / 31 / 144 | 22 / 35 / 138 |
| Letras | 18 / 38 / 144 | 22 / 43 / 138 |

Estas coordenadas se estimaron de las fotos y deben verificarse con una prueba.
Los parámetros `offset_x` y `offset_y` siguen disponibles en QWeb para compensar
un desplazamiento constante después de fijar el papel, sin cambiar numeración.

Desde 18.0.1.0.1 se utiliza **96 DPI**, con `data-report-dpi="96"` en el HTML para
evitar el factor adicional `96 / dpi` del generador de Odoo. La posición relativa,
el tamaño y la fuente van directamente en cada `.article`, porque Odoo extrae
esos bloques a su layout mínimo y no conserva el estilo del encabezado original.
## Monto gráfico en 18.0.1.0.10

El cliente confirma que el PDF contiene el importe completo, pero en la Epson
solo sale el primer dígito, incluso en una hoja Carta completa y sin ajuste
al ancho. Esa prueba descarta que el borde del cheque sea la única explicación;
no identifica por sí sola el defecto exacto del visor o controlador.

Esta revisión imprime **solo el monto numérico mediante imágenes PNG** de los
10 dígitos, la coma y el punto. Cada carácter conserva su avance y posición
absoluta dentro del mismo campo. El PDF resultante no contiene ese monto como
texto: el controlador no puede sustituir sus caracteres por fuentes residentes.
Se mantienen las posiciones de 1.0.9, anchos, tamaño configurado, reducción para
importes largos y las validaciones del pago. Fecha, beneficiario y letras siguen
siendo texto y no se cambian. La rasterización puede variar ligeramente el trazo.

Las 12 imágenes están embebidas en el XML, sin archivos de fuentes ni dependencias
nuevas de servidor. `checks/build_amount_glyphs.py` de la extensión LX-350 es una
herramienta de construcción offline que requiere Pillow y Arial Bold; no forma
parte del ZIP importable ni se ejecuta dentro de Odoo. La producción sigue usando
únicamente XML y los modelos ya instalados.

El importe numérico deja de ser seleccionable como texto en el PDF. El valor
numérico del pago y su representación en letras se conservan. Se verifican los
separadores y cada cifra en las pruebas de geometría y en el PDF renderizado.

Se entrega aparte `Prueba_monto_grafico_1578_85.pdf`, generado con las expresiones
XML y datos ficticios, para probar en papel común antes de importar. Usa la misma
posición G&T y la leyenda PRUEBA SIN VALOR. El render local confirma ocho imágenes
para 1,578.85 y nueve para 81,689.69, sin recorte y con el resto de campos idénticos.
Falta validar la nueva salida gráfica en la Epson real y el importador de Odoo.
La extensión USB completa conserva su implementación independiente.

## Ajuste fino G&T en 18.0.1.0.9

Según la nueva prueba G&T, monto en números, beneficiario e importe en letras
se desplazan **2 mm a la izquierda y 2 mm hacia abajo** respecto de 1.0.8.
La fecha, los tamaños de letra, anchos, contenido y perfil Banrural se conservan.
En G&T, el monto usa base 135 mm + compensación 20 mm = 155 mm de plantilla;
Banrural conserva base 137 mm + 20 mm = 157 mm. Este ajuste se estima a partir
de la petición y fotografía; no se indicó una distancia física exacta.

## Antecedente: ajuste intermedio del monto en 18.0.1.0.8

Se midieron los archivos descargados del servidor que el usuario comparó:

| PDF | Inicio / final del monto desde la izquierda de la página (mm) |
|---|---|
| Banrural de la primera captura, copia `-2` | 139.17 / 162.00 |
| Banrural anterior, copia `-3` y `-4` | 141.02 / 163.85 |
| Banrural personal v1.0.5 | 141.02 / 159.82 |

Entre las dos capturas (`-2` y v1.0.5), el movimiento fue de solo 1.85 mm.
Entre las copias `-3`/`-4` y v1.0.5, el inicio no cambió: el nuevo tipo de letra
solo redujo el ancho. La configuración
base de 137 mm no representaba un corrimiento adicional respecto a esa impresión.
Ambos archivos son Carta, 215.9 × 279.4 mm. La envoltura del servidor agrega unos
4 mm al origen horizontal de la plantilla; la reproducción local anterior no los
incluía. La causa exacta de la diferencia entre el PDF y la foto impresa no puede
certificarse sin medir una salida física de referencia. El usuario confirma
Carta en el controlador y 100 % en el visor.

La versión 18.0.1.0.7 agregó 40 mm solo al monto: base 137 mm + compensación
40 mm = 177 mm de plantilla. La reproducción con el origen del servidor midió
141.02 → 180.97 mm. El cliente informa que esa salida quedó demasiado a la derecha.

La versión 18.0.1.0.8 reduce la compensación a **20 mm**: base 137 mm + 20 mm =
**157 mm de plantilla**, medidos en 161.13 mm en el PDF de prueba con la
envoltura del servidor. El retroceso medido es 19.84 mm respecto de 1.0.7. Es un retroceso de unos **20 mm respecto de 1.0.7**, elegido como punto
intermedio entre la impresión inicial y la última prueba. No es una medición
física nueva: no se proporcionó otra fotografía o distancia exacta.

Se conserva el ancho de 25 mm, la fuente, el tamaño y la altura del monto;
los otros campos tampoco se desplazan. Se valida el área nominal por separado
y el monto compensado contra el lienzo Carta (hasta 202 mm de plantilla).

**Esta es una compensación para la salida que el cliente está observando**, no
una medida certificada del campo impreso del cheque. No se cambia el tamaño
nominal del cheque a 216 mm. Antes de usar originales:

1. Imprimir `Prueba_corrimiento_monto_40mm_Carta.pdf` en papel común, Carta / 100 %.
2. La barra de referencia debe medir 100 mm. Los inicios de ambos importes deben
   quedar separados horizontalmente por 40 mm (sus filas son distintas).
3. Si las medidas no coinciden, hay escala posterior en el visor/controlador:
   no se garantiza que 40 mm del PDF sean 40 mm sobre el papel.
4. Descargar un PDF nuevo v1.0.10. En G&T, los tres campos deben verse 2 mm a la izquierda y 2 mm más abajo respecto de 1.0.8.
   Probar en papel común antes de comprobarlo con el cheque.
5. Conservar colocación del papel y configuración. Si se corrige posteriormente
   el origen o la escala de la impresora, recalibrar o quitar `amount_shift_x`.

El PDF de prueba se entrega aparte del módulo y utiliza datos ficticios.

Desde 18.0.1.0.3, fecha, beneficiario y monto usan hasta **12 pt**, y el importe
en letras hasta **11 pt**. Desde 18.0.1.0.5 se cambia Courier New por
**Arial negrita**, con alternativa Liberation Sans y tamaños enteros. El cálculo
de ancho desde 18.0.1.0.6 usa avances de caracteres de la familia sans-serif
negrita en milésimas de em, con una reserva del 4 % y el espaciado explícito.
Sustituye la estimación por categorías de 18.0.1.0.5. Los textos
largos se reducen hasta 9 pt; si no caben se genera el aviso de revisión en lugar de truncarlos. En QWeb,
`font_sizes` contiene los tamaños de cada campo y `min_font` el mínimo permitido.

La versión 18.0.1.0.5 podía rechazar el mismo pago solo en G&T: el texto
«OCHENTA Y UN MIL SEISCIENTOS OCHENTA Y NUEVE QUETZALES CON 69/100» se estimaba
en 141.27 mm a 9 pt, mayor que los 138 mm de G&T pero menor que los 144 mm de
Banrural. El cálculo corregido estima 135.50 mm incluyendo la reserva y el
espaciado; cabe en ambos perfiles sin cambiar posiciones, anchos ni mínimo de
letra. Se agrega esa regresión a las pruebas. Los avisos ahora distinguen datos
del pago, posiciones y cada campo que no cabe, con su ancho necesario y disponible.

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

La posición física continúa pendiente de verificación. La revisión 1.0.8
reduce a la mitad la compensación de 1.0.7, sin atribuir el problema
a un cambio de tamaño que todavía no se ha demostrado. Los botones y nombres
de descarga incluyen v1.0.10 para identificar la actualización.

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
- `amount_shift_x`: compensación horizontal solo del monto; 20 mm en 1.0.8 (40 mm en 1.0.7).
  Usar 0 para volver a la posición de 1.0.6; no escalar la fuente para moverlo.
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
real no se ha ejecutado aquí. Se midieron los PDF reales descargados del servidor
y se reproduce también un padding horizontal de 16 px para verificar el delta
entre revisiones con la envoltura observada. No sustituye una prueba física.
Las imágenes con datos bancarios y firmas no se incluyen en el paquete.

Fuentes:

- [Odoo 18: tamaños de papel](https://github.com/odoo/odoo/blob/18.0/odoo/addons/base/models/report_paperformat.py).
- [Odoo 18: importación de módulos de datos](https://github.com/odoo/odoo/blob/18.0/addons/base_import_module/models/ir_module.py).
- [Epson LX-350: fuentes residentes, mapa de bits y calidad del controlador](https://files.support.epson.com/htmldocs/lx350_/lx350_ug/html/soft_4.htm).
