{
    "name": "POS Internal Correlative",
    "summary": "Correlativo interno para pedidos del POS; se copia a la factura y se imprime en el recibo.",
    "version": "18.0.1.0.2",
    "category": "Point of Sale",
    "author": "Tu Equipo",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "account"],
    "data": [
        "data/ir_sequence.xml",
        "views/pos_order_views.xml",
        "views/account_move_views.xml",
        "views/pos_config_views.xml",   # <- añade esta línea
    ],

    
    "assets": {
        "point_of_sale.assets": [
            "pos_internal_correlative/static/src/js/pos_correlative.js",
            "pos_internal_correlative/static/src/js/receipt_header_data_patch.js",
            "pos_internal_correlative/static/src/xml/pos_receipt.xml",
            "pos_internal_correlative/static/src/xml/receipt_header_patch.xml",
        ],
    },

    "installable": True,
    "application": False,
}
