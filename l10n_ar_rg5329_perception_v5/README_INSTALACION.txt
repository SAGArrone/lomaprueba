Modulo: l10n_ar_rg5329_perception_v5

Uso recomendado:
1. Subir la carpeta completa l10n_ar_rg5329_perception_v5 al repositorio/addons de Odoo.sh.
2. Actualizar lista de aplicaciones.
3. Instalar "Argentina - Percepcion IVA RG 5329/2023 V5".
4. En Contabilidad > Configuracion > Ajustes configurar:
   - Habilitar RG 5329.
   - Cuenta contable de percepcion.
   - Grupo de impuestos.
   - Importe minimo.
   - Responsabilidades alcanzadas.
   - Categorias alcanzadas, opcional.

Diferencias principales contra V4:
- No usa onchange invalido invoice_line_ids.product_id.
- Calcula por base acumulada por alicuota.
- Mantiene un motor central en account.move.
- El onchange de account.move.line solo fuerza recalculo del motor central.
- La percepcion no se asigna a productos.

Prueba sugerida:
- Cliente Responsable Inscripto alcanzado.
- Dos lineas con IVA 21%: 100000 y 50000.
- Si el minimo configurado corresponde, debe agregar la percepcion 3% a ambas lineas alcanzadas, tomando base acumulada 150000.
