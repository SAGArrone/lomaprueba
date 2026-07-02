Modulo: Argentina - Percepcion IVA RG 5329/2023 V5.2

Objetivo
- Calcular automaticamente la percepcion de IVA RG 5329/2023 en facturas de cliente.
- La validacion se realiza por acumulado de factura y alicuota de IVA, no por subtotal individual de linea.
- Soporta Odoo 19, donde las lineas comerciales pueden tener display_type='product'.

Alcance funcional
- Aplica solo en facturas de cliente en borrador (out_invoice).
- Aplica si el cliente esta dentro de los tipos de responsabilidad configurados.
- Aplica si la factura usa documento fiscal argentino alcanzado.
- Aplica por alicuota:
  - IVA 21% -> percepcion 3%.
  - IVA 10,5% -> percepcion 1,5%.
- El importe minimo se compara contra la percepcion calculada sobre la base acumulada de cada alicuota.

Categorias de productos
- La configuracion permite seleccionar categorias alcanzadas.
- Si no se seleccionan categorias, se consideran todas las categorias existentes.
- Importante: los productos sin categoria no son considerados por el regimen. Si un producto figura como sin categoria / sin ninguna, no se suma a la base acumulada y no recibe percepcion.
- Para evitar diferencias, todos los productos alcanzados deben tener una categoria cargada.

Notas tecnicas
- El calculo se centraliza en account.move.
- El onchange de account.move.line no decide la percepcion por linea; solo dispara el recalculo centralizado.
- El metodo _l10n_ar_rg5329_invoice_base_lines inspecciona invoice_line_ids y line_ids para ser compatible con onchange/web_save de Odoo 19.
- No se asignan percepciones automaticamente al producto; se agregan y limpian dinamicamente en la factura.

Instalacion / actualizacion
1. Subir la carpeta completa l10n_ar_rg5329_perception_v5 al repositorio de Odoo.sh.
2. Actualizar lista de aplicaciones.
3. Instalar o actualizar el modulo Argentina - Percepcion IVA RG 5329/2023 V5.2.
4. Configurar desde Contabilidad > Ajustes.
5. Verificar cuenta contable, grupo de impuestos, importe minimo, tipos de contribuyentes y categorias alcanzadas.
