# -*- coding: utf-8 -*-
{
    "name": "Account Payment: Partner Counterpart (AR/AP)",
    "summary": "Al postear pagos usa CxC/CxP del partner como contrapartida y deja la otra línea en la cuenta de banco.",
    "version": "18.0.1.0.2",
    "author": "Velfasa / Estuardo & ChatGPT",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": [
        "account",
        # asegurar que este addon cargue después de los que también sobreescriben el método
        "account_payment_order",                 # tu custom en reportescustom
        "pos_force_close_session",               # tu custom en Prueba-blocks
        "account_payment_direct_liquidity"       # tu custom en Prueba-blocks
    ],
    "data": [],
    "installable": True
}
