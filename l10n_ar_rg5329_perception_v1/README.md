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
Luego de cambiar las categorias alcanzadas se puede usar el boton "Asociar impuestos"
para asociar las percepciones RG 5329 a productos existentes segun categoria e IVA.

## Criterio de calculo

El producto conserva la percepcion RG 5329 como impuesto informativo segun categoria e IVA.
Al cargar una factura, el modulo la quita o agrega dinamicamente en las lineas segun
cliente, documento legal y base agregada por alicuota:

- IVA 21%: percepcion 3%.
- IVA 10,5%: percepcion 1,5%.

La percepcion solo se mantiene en la factura si el importe calculado supera el minimo configurado para la compania.

Ademas, en factura solo aplica cuando el cliente tiene una responsabilidad fiscal alcanzada
y la factura usa un diario de venta argentino con documentos y punto de venta de ARCA.
Si alguna condicion deja de cumplirse, el modulo quita la percepcion RG 5329 de la linea.
