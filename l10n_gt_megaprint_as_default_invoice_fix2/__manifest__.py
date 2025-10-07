{
  "name": "GT Megaprint como factura por defecto (print + email) [FIX2]",
  "summary": "Sustituye la impresión y el PDF del correo de factura por el reporte Megaprint.",
  "version": "18.0.1.2",
  "license": "LGPL-3",
  "author": "Estuardo & ChatGPT",
  "depends": ["account", "l10n_gt_fel_megaprint_report"],
  "data": [],
  "post_init_hook": "post_init_set_megaprint_invoice",
  "uninstall_hook": "uninstall_restore_default_invoice",
  "installable": True,
  "application": False
}