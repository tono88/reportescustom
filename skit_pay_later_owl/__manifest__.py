{
    "name": "SKIT Pay Later (OWL, POS 18)",
    "summary": "Botón 'Pagar después' para POS 18 (OWL) sin jQuery/Bootstrap.",
    "version": "18.0.1.0",
    "category": "Point of Sale",
    "author": "ChatGPT (port for Estuardo)",
    "website": "https://example.com",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "skit_pay_later_owl/static/src/css/pay_later.css",
            "skit_pay_later_owl/static/src/js/payment_pay_later.js",
            "skit_pay_later_owl/static/src/js/recall_pay_later.js",
            "skit_pay_later_owl/static/src/xml/payment_pay_later.xml",
            "skit_pay_later_owl/static/src/xml/recall_button.xml"
        ]
    },
    "installable": true,
    "application": false
}