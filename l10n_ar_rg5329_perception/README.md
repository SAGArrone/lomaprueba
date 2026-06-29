# Argentina - Percepcion IVA RG 5329/2023

Modulo Odoo 19 para habilitar opcionalmente el regimen de percepcion IVA RG 5329/2023 desde Contabilidad.

## Configuracion

Ir a Contabilidad > Configuracion > Ajustes > Localizacion Argentina y activar "Percepcion IVA RG 5329/2023".

Campos principales:

- Cuenta contable de percepcion.
- Grupo de impuestos.
- Importe minimo de percepcion, por defecto 3000.
- Tipos de contribuyentes alcanzados.
- Categorias de productos alcanzadas.

Al habilitar el regimen se crean, si no existen, los impuestos de venta RG 5329 del 3% y 1,5%.

## Criterio de calculo

El modulo agrega o quita la percepcion en las lineas de factura segun la base agregada por alicuota:

- IVA 21%: percepcion 3%.
- IVA 10,5%: percepcion 1,5%.

La percepcion solo se mantiene en la factura si el importe calculado supera el minimo configurado para la compania.

