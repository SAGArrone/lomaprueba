# Argentina - Percepcion IVA RG 5329/2023

Modulo Odoo 19 para habilitar opcionalmente el regimen de percepcion IVA RG 5329/2023 desde Contabilidad.

## Funcionamiento

El modulo no usa `post_init_hook`: al instalar no modifica impuestos ni productos. Solo comienza a funcionar cuando se habilita desde Ajustes de Contabilidad.

La percepcion RG 5329 no se graba en productos. Se calcula dinamicamente en facturas de cliente, porque depende de:

- responsabilidad fiscal del cliente;
- categorias de productos alcanzadas;
- alicuota de IVA de cada linea;
- importe minimo de percepcion configurado.

## Criterio

- IVA 21%: percepcion 3%.
- IVA 10,5%: percepcion 1,5%.
- Solo aplica cuando la percepcion calculada supera el minimo configurado.
- Si no se configuran categorias, se consideran alcanzados todos los productos.
- Si el cliente no esta alcanzado, se eliminan percepciones RG 5329 de las lineas.

El boton de configuracion limpia percepciones RG 5329 que hayan quedado cargadas en productos de versiones anteriores.
