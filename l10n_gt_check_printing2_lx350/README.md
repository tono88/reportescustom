# Cheques personales Banrural y G&T / Epson LX-350 — Odoo 18 Community

Extensión de `l10n_gt_check_printing2`. Agrega diseños propios para cheques
preimpresos Banrural y G&T Continental, posiciones por diario y envío del PDF a una impresora USB
local mediante QZ Tray. Puede coexistir con `l10n_gt_check_printing2_voucher`.

## Instalación en Windows

1. Realizar copia de seguridad de la base y probar primero en una copia.
2. Copiar la carpeta `l10n_gt_check_printing2_lx350` a una ruta incluida en
   `addons_path`. No reemplazar los módulos existentes.
3. Reiniciar el servicio Odoo, actualizar la lista de aplicaciones, quitar el
   filtro Aplicaciones e instalar **Guatemala - Cheques personales Banrural y G&T / Epson LX-350**.
   El Python del servicio debe tener `num2words`, usado también por Odoo.
4. Instalar el controlador oficial Epson LX-350 en la computadora conectada por
   USB. Comprobar primero la impresión desde Windows.
5. Instalar y abrir [QZ Tray](https://qz.io/download/) 2.3.x en esa computadora.
   La biblioteca JavaScript 2.3.0 está incluida localmente; no utiliza un CDN.
6. En Contabilidad / Configuración / Diarios, abrir cada diario de la empresa
   correcta. En pagos salientes, habilitar Cheques y seleccionar el diseño del
   banco correspondiente:
   - Diario Banrural: **Banrural / LX-350 — Personal 165.10 × 69.85 mm**.
   - Diario G&T: **G&T Continental / LX-350 — Personal 165.10 × 69.85 mm**.
   Si la opción de impresión no aparece, activar Cheques en los ajustes contables.
7. Para cheques ya numerados por el banco, dejar desmarcada la opción de
   numeración manual (la ayuda de Odoo indica que se usa para papel sin número).
   Conservar el asistente que solicita el primer número preimpreso.

El diseño del diario prevalece sobre el diseño de empresa, incluso cuando la
empresa conserva un diseño GT2 anterior. No se cambia automáticamente ninguna
empresa, diario, pago, cuenta bancaria ni numeración al instalar.

## Tamaño y alimentación

Se incluyen **dos formatos personales de 165.10 × 69.85 mm**, uno para Banrural
y otro para G&T Continental, con acciones y botones separados. Ambos tamaños
personales se toman como punto de partida indicado por el usuario; las fotos no
certifican una medida física. Las posiciones iniciales de cada banco son
aproximadas a partir de sus fotografías y requieren calibración física. Los
reportes GT2 anteriores permanecen disponibles.

La LX-350 especifica un mínimo de **100 × 100 mm para hojas sueltas estándar**.
El cheque desprendido, de 69.85 mm de alto, queda fuera de ese rango. Configurar
un PDF pequeño no resuelve esa limitación mecánica: antes de imprimir originales
debe validarse una alimentación compatible con Epson y el proveedor del papel.
Si se utiliza un formulario mayor con talón/soporte, se requiere adaptar también
el formato de página al formulario completo y recalibrar el origen; estos diseños
representan exclusivamente el cuerpo del cheque. No se promete alimentación de
cheques sueltos ni se incluye un soporte físico.

## Calibración

En cada diario, en **Calibración de cheques personales / Epson LX-350**:

Seleccionar el diseño del banco y pulsar **Cargar posiciones iniciales del banco**.
Esta acción reemplaza la calibración de ese diario, con confirmación. Cargar el
perfil al configurar por primera vez; después ajustar los valores y conservarlos.
Cambiar de banco en el selector no reemplaza automáticamente posiciones ya
calibradas. Los ajustes de un diario no afectan al del otro banco ni otra empresa.

1. Usar **PDF de prueba** sobre papel común. Incluye datos ficticios y la leyenda
   PRUEBA SIN VALOR. No requiere crear pagos ni asigna números.
2. Imprimir al 100 %, sin ajustar, centrar ni escalar automáticamente. Definir
   el mismo tamaño de papel en el controlador y mantener una posición fija de
   la guía lateral. No utilizar el original firmado de la fotografía como prueba.
3. Comparar con el cheque y ajustar por diario:
   - Desplazamiento horizontal negativo: mueve a la izquierda.
   - Desplazamiento vertical positivo: mueve hacia abajo.
   - X/Y y ancho de cada campo: fecha, monto, beneficiario y letras.
   - Lugar de emisión (PALÍN inicialmente) y letra de 7 a 12 puntos.
4. **Configurar Epson USB**: autorizar QZ Tray y elegir el nombre exacto de la
   impresora instalada. Se guarda por navegador, usuario y empresa. El nombre
   de la cola no tiene que ser literalmente EPSON LX-350.
5. Usar **Prueba en Epson USB** sobre papel común antes de imprimir originales.

Las posiciones se miden desde la esquina superior izquierda del cuerpo del
cheque, en milímetros. Son independientes de los márgenes globales del GT2.
No se imprime banco, cuenta, firma, numeración bancaria ni banda MICR. La banda
inferior de 16 mm se reserva para la información preimpresa. Se rechazan campos
fuera de los límites; nunca se recortan silenciosamente beneficiario o letras.
El tamaño de letra puede reducirse hasta 7 pt para textos largos; la estimación
es conservadora y la prueba física sigue siendo necesaria.

## Impresión y recuperación

- **Imprimir cheque** conserva el flujo habitual y descarga PDF con el nuevo
  diseño si el diario tiene seleccionado Banrural o G&T / LX-350.
- **Imprimir Banrural USB** aparece en pagos del diario con diseño Banrural.
- **Imprimir G&T USB** aparece en pagos del diario con diseño G&T.
  Son dos botones y acciones distintos. Cada uno conserva el asistente de
  numeración y envía una copia al destino guardado, sin escala automática.
  El servidor rechaza usar el botón del otro banco, incluso si se llama por API.
  Para cambiar de banco, usar el diario/cuenta bancaria correcto del pago; el
  botón no convierte un pago Banrural en un pago de G&T.
- **PDF del cheque asignado** descarga el mismo cheque sin cambiar su número.
- **Reimprimir mismo cheque USB** pide confirmar y reutiliza el número asignado;
  comprobar primero la cola y el papel para evitar duplicados.

Odoo marca el pago como enviado durante su flujo de numeración, antes de que el
dispositivo termine. Un error o cancelación posterior no revierte ni reasigna
números. La aceptación por QZ/Windows significa **enviado a la cola**, no prueba
de que el papel haya salido. Nunca se reintenta automáticamente ni se manda una
segunda copia como fallback. El bloqueo de doble clic es por pestaña; no es una
garantía de exclusión entre computadoras o pestañas distintas.

El reporte comprueba permisos de lectura, empresa y diario únicos, pago saliente
mediante cheque, moneda GTQ, beneficiario, estado confirmado y número asignado.
Las pruebas utilizan documentos `account.journal` y no alteran la contabilidad.

## Autorizaciones de QZ y privacidad

La integración entrega el PDF al puente en base64 desde una sesión autenticada;
no publica el cheque ni pasa cookies de Odoo a QZ. Solo se interceptan reportes
de este módulo cuando se usa el botón USB. No se cambia la impresora de otros
reportes ni la predeterminada de Windows.

Esta versión utiliza el flujo de autorización estándar de QZ Tray. **No incluye
firma de confianza ni promete impresión silenciosa sin avisos.** Para quitar los
avisos debe implementarse firma de mensajes y configurar un certificado de
confianza; puede implicar un certificado comercial o una infraestructura propia.
No se incluyen claves privadas ni se desactivan las autorizaciones del puente.

## Voucher

El módulo de voucher existente conserva su acción de reporte separada. Imprimir
el cheque desde el pago y obtener el comprobante desde el menú Imprimir con la
acción **Cheque Guatemala 2 + Voucher**. No enviar el comprobante sobre el cheque.
El módulo voucher del repositorio tiene los modelos sin importar en su
`__init__.py`; esta extensión no cambia esa implementación ni garantiza que las
opciones de diseño de voucher aparezcan en la lista de empresa.

## Verificación

Comprobaciones locales sin Odoo:

```text
python -m unittest discover -s l10n_gt_check_printing2_lx350/checks -p "test_*.py"
node --test l10n_gt_check_printing2_lx350/checks/printing.test.cjs
```

Las pruebas de integración se incluyen en `tests/` para ejecutarlas con Odoo 18
y una base de pruebas (`--test-tags /l10n_gt_check_printing2_lx350`). En este
entorno no hay servidor Odoo, PostgreSQL ni wkhtmltopdf: instalación, render PDF
y funcionamiento físico quedan pendientes de esa validación. El módulo se
entrega para probar y calibrar, no como una impresora ya configurada a distancia.

## Fuentes y terceros

- [Banco de Guatemala, resolución 60-2023, apartado 4.1](https://banguat.gob.gt/sites/default/files/banguat/Publica/SPagos/GG_60-2023.pdf).
- [Epson LX-350: papel y área imprimible](https://files.support.epson.com/htmldocs/lx350_/lx350_ug/html/apspe_2.htm).
- [QZ Tray: impresión PDF, tamaños y escala](https://qz.io/docs/pixel).
- [QZ Tray: firma](https://qz.io/docs/signing).
- Biblioteca `static/lib/qz-tray/qz-tray.js`: QZ Industries, versión 2.3.0,
  LGPL-2.1-only. Fuente: https://github.com/qzind/tray/blob/v2.3.0/js/qz-tray.js.
  Licencia y atribuciones originales incluidas junto al archivo, sin modificar.
