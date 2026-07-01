<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <data>
        <record id="res_config_settings_view_form" model="ir.ui.view">
            <field name="name">res.config.settings.view.form.inherit.account</field>
            <field name="model">res.config.settings</field>
            <field eval="40" name="priority"/>
            <field name="inherit_id" ref="account.res_config_settings_view_form"/>
            <field name="arch" type="xml">
                <xpath expr="//app[@name='account']" position="inside">
                    <block title="AFIP Web Services" name="l10n_ar_afipws_settings">
                        <setting string="Entorno AFIP" help="Configura el entorno usado para autenticacion y consultas de padron AFIP.">
                            <field name="afip_ws_env_type" class="fw-bold"/>
                            <div class="mt16">
                                <button class="btn btn-link" icon="fa-arrow-right" name="%(l10n_ar_afipws.act_afipws_certificate_alias)d" string="Lista certificados" type="action"/>
                                <button class="btn btn-link" icon="fa-arrow-right" name="%(l10n_ar_afipws.act_afipws_auth)d" string="Lista conexiones" type="action"/>
                            </div>
                        </setting>
                    </block>
                </xpath>
            </field>
        </record>
    </data>
</odoo>
