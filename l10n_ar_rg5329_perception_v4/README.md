# Argentina - Percepcion IVA RG 5329/2023

Modulo Odoo 19 para habilitar opcionalmente el regimen de percepcion IVA RG
5329/2023 desde Contabilidad.

## Funcionamiento

El modulo no usa `post_init_hook`: al instalar no modifica impuestos ni
productos. Solo comienza a funcionar cuando se habilita desde Ajustes de
Contabilidad.

El impuesto RG 5329 queda asociado al producto como referencia informativa segun
categoria alcanzada e IVA de venta. Al cargar una factura, el modulo quita o
agrega dinamicamente la percepcion de las lineas segun:

- responsabilidad fiscal del cliente;
- diario de venta con documentos y punto de venta de ARCA;
- tipo de documento legal de factura;
- categorias de productos alcanzadas;
- alicuota de IVA de cada linea;
- importe minimo de percepcion configurado.

## Criterio

- IVA 21%: percepcion 3%.
- IVA 10,5%: percepcion 1,5%.
- La base se acumula por alicuota de IVA en toda la factura.
- Si dos lineas de IVA 21% suman $150.000, la percepcion 3% aplica sobre las
  lineas alcanzadas de IVA 21%.
- Aplica cuando la percepcion calculada alcanza o supera el minimo configurado.
- Si el cliente no esta alcanzado, se eliminan percepciones RG 5329 de las
  lineas.
- Si al editar importes el acumulado queda por debajo del minimo, se quita la
  percepcion.

El boton de configuracion "Asociar impuestos" actualiza los productos existentes
segun categorias alcanzadas e IVA.
