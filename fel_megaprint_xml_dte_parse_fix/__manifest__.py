# -*- coding: utf-8 -*-
{
    'name': 'FEL Megaprint XML DTE Parse Fix',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations',
    'summary': 'Compatibilidad robusta para leer NumeroAutorizacion desde xml_dte Megaprint/IFACERe',
    'description': """
Patch seguro para fel_megaprint.

Este módulo no modifica vistas ni flujo de facturación. Solamente hace más robusta
la lectura de NumeroAutorizacion desde xml_dte cuando el certificador devuelve el
XML escapado, doblemente escapado, con namespaces distintos o envuelto en CDATA.
    """,
    'author': 'Custom BLK',
    'license': 'LGPL-3',
    'depends': ['fel_megaprint'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
