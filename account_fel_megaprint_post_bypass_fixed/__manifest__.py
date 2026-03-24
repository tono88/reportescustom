{
    'name': 'Account FEL Megaprint Post Bypass',
    'version': '18.0.1.1.0',
    'summary': 'Contabiliza documentos ya certificados sin volver a esperar/certificar FEL Megaprint.',
    'description': """
Módulo administrativo para Odoo 18 Community.

Objetivo:
- Permitir contabilizar facturas o notas de crédito que ya fueron certificadas en FEL Megaprint
  y luego quedaron en borrador, sin volver a certificar ni esperar respuesta del certificador.

Qué hace:
- Agrega el botón 'Contabilizar sin recertificar FEL'.
- Ejecuta el posteo contable base de account.move de forma directa cuando se usa el bypass.
- Omite el método certificar_megaprint durante el bypass.
- Evita módulos intermedios que bloquean el posteo esperando la certificación FEL.

Uso recomendado:
- Solo para casos administrativos controlados.
- Usar únicamente cuando el documento ya tenga FEL previo.
- Probar primero en desarrollo antes de usar en producción.
""",
    'author': 'OpenAI',
    'website': 'https://openai.com',
    'category': 'Accounting/Accounting',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'fel_megaprint',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
}
