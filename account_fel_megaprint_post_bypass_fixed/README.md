# Account FEL Megaprint Post Bypass v2

## Qué corrige esta versión
La versión anterior solo omitía `certificar_megaprint()`. Esta versión además evita el flujo que bloquea el posteo esperando una respuesta FEL.

## Cómo trabaja
- El botón llama `action_post_without_fel()`.
- Se valida que el documento esté en borrador y tenga alguna referencia FEL previa.
- Se ejecuta directamente el `_post()` base de `account.move`.
- Si algún otro flujo vuelve a llamar `_post()` con el contexto de bypass, también se usa el core de `account`.

## Recomendación
Usar solo cuando la factura ya fue certificada anteriormente y únicamente se necesita volverla a estado contabilizado/posteado.
