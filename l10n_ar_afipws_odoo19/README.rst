=========================================
AFIP Web Services Base - Argentina Odoo 19
=========================================

Modulo base para conectar Odoo 19 con Web Services de AFIP/ARCA.

Esta version mantiene la logica original del modulo y aplica solo ajustes de
compatibilidad para Odoo 19, Python 3 y Odoo.sh.

Alcance funcional
=================

El modulo permite:

* Configurar el entorno AFIP: homologacion o produccion.
* Administrar alias de certificados AFIP.
* Generar clave privada y solicitud CSR.
* Cargar certificados emitidos por AFIP.
* Obtener y reutilizar conexiones/token/sign para servicios AFIP.
* Consultar padron AFIP desde contactos.
* Actualizar datos del contacto desde padron AFIP.
* Consultar estado MiPyME para factura de credito electronica.

Servicios incluidos
===================

El modelo ``afipws.connection`` mantiene soporte para:

* ``ws_sr_padron_a4``
* ``ws_sr_padron_a5``
* ``ws_sr_constancia_inscripcion``
* ``wsfecred``

Los servicios ``ws_sr_padron_a10`` y ``ws_sr_padron_a100`` aparecen en la
seleccion, pero no tienen implementacion de URL ni cliente en este modulo base.
Se conservan para no cambiar la logica original y permitir extension por otros
modulos.

Instalacion en Odoo.sh
======================

1. Copiar la carpeta ``l10n_ar_afipws`` dentro del directorio de addons custom
   del repositorio de Odoo.sh.

2. Agregar las dependencias Python en el archivo ``requirements.txt`` del root
   del repositorio Odoo.sh::

      pyafipws
      pyOpenSSL
      pysimplesoap
      httplib2

   El archivo ``requirements.txt`` incluido dentro de este modulo es solo una
   referencia. Odoo.sh instala dependencias desde el ``requirements.txt`` del
   repositorio, no desde el manifest del modulo.

   Para permitir instalar el modulo desde el importador de Apps, esta version no
   declara ``pyafipws`` como ``external_dependencies`` en el manifest. Esto evita
   que Odoo bloquee la instalacion. De todos modos, las consultas reales a AFIP
   requieren que ``pyafipws`` este instalado en el servidor.

3. Subir los cambios al repositorio y esperar el build de Odoo.sh.

4. Actualizar lista de aplicaciones.

5. Instalar ``Modulo Base para los Web Services de AFIP``.

Dependencias Odoo
=================

El modulo declara dependencia de:

* ``account``
* ``contacts``
* ``l10n_ar``

Tambien requiere que la base tenga configurada la localizacion argentina y que
la compania tenga CUIT valido.

Configuracion funcional
=======================

1. Ir a ``Contabilidad > Configuracion > Ajustes``.

2. En el bloque ``AFIP Web Services`` seleccionar:

   * ``homologation`` para pruebas.
   * ``production`` para operar contra AFIP/ARCA real.

3. Ir a ``AFIP Web Services > Certificates``.

4. Crear un alias de certificado:

   * Compania.
   * Tipo: homologacion o produccion.
   * CUIT de la compania o proveedor de servicio.
   * Ciudad/provincia/pais.

5. Confirmar el alias. El sistema genera la clave privada.

6. Crear la solicitud de certificado. Descargar el CSR.

7. Cargar el CSR en AFIP/ARCA y descargar el certificado emitido.

8. En Odoo, abrir el certificado y usar ``Upload Certificate`` para cargar el
   archivo emitido por AFIP/ARCA.

Uso funcional
=============

Consulta de padron
------------------

Desde un contacto con CUIT:

1. Abrir el contacto.
2. Usar el boton ``DATOS AFIP``.
3. Elegir los campos a actualizar.
4. Ejecutar actualizacion manual o automatica.

MiPyME / Factura de credito
---------------------------

Desde un contacto:

1. Abrir la pestana contable del contacto.
2. Usar ``Check mi Pyme status``.
3. El sistema consulta ``wsfecred`` y actualiza:

   * ``Must credit invoice``.
   * ``Credit invoice from amount``.

Documentacion tecnica
=====================

Modelos principales
-------------------

``afipws.certificate_alias``
    Alias/DN AFIP. Genera clave privada y solicitudes CSR.

``afipws.certificate``
    Certificado AFIP vinculado a un alias.

``afipws.connection``
    Token/sign y datos de conexion para cada Web Service.

``res.company``
    Define entorno AFIP, obtiene certificados y autentica contra WSAA.

``res.partner``
    Consulta padron AFIP y actualiza datos de contacto.

``res.partner.update.from.padron.wizard``
    Wizard de actualizacion manual/automatica desde padron.

Parametros tecnicos
-------------------

``afip.ws.env.type``
    Parametro de sistema con valores ``homologation`` o ``production``.

Si el parametro no existe, el modulo conserva la logica original:

* ``server_mode`` vacio o ``production`` usa produccion.
* Cualquier otro ``server_mode`` usa homologacion.

Certificados desde archivo de configuracion
-------------------------------------------

Si no existe certificado confirmado en base de datos, el modulo intenta leer:

* ``afip_prod_pkey_file``
* ``afip_prod_cert_file``
* ``afip_homo_pkey_file``
* ``afip_homo_cert_file``

Estos parametros se leen desde la configuracion del servidor Odoo.

Notas de migracion a Odoo 19
============================

Cambios aplicados sobre la version 18:

* Manifest actualizado a serie ``19.0``.
* Dependencias Odoo explicitas: ``account`` y ``contacts``.
* Vista de ajustes migrada a estructura ``app/block/setting`` de Odoo 19.
* Vistas listas mantenidas con ``<list>``.
* Compatibilidad Python 3 en manejo de excepciones.
* Conversion segura de certificados y claves entre ``bytes`` y texto PEM.
* Correccion de generacion de archivo CSR descargable.

No se cambio la logica de negocio del modulo.

Problemas frecuentes
====================

Falta dependencia Python
------------------------

Si Odoo informa que falta ``pyafipws``, ``OpenSSL`` o ``pysimplesoap``, revisar
el ``requirements.txt`` del repositorio Odoo.sh y volver a ejecutar el build.

No aparece el bloque de configuracion
-------------------------------------

Actualizar lista de aplicaciones y actualizar el modulo. El bloque se agrega en
ajustes de Contabilidad.

AFIP no responde
----------------

El modulo conserva la accion de ayuda que abre la consulta manual de constancia
AFIP/ARCA cuando el servicio no esta disponible.

Campos de padron no encontrados
-------------------------------

La actualizacion de padron usa campos de localizacion argentina como
``imp_iva_padron``, ``imp_ganancias_padron``, ``actividades_padron`` e
``impuestos_padron``. Si la base no los tiene, instalar primero el modulo de
localizacion que los provee o extender este modulo con esos campos.

Licencia
========

AGPL-3
