<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="action_base_partner_update_from_padron" model="ir.actions.act_window">
        <field name="name">Update Partners From Padron AFIP</field>
        <field name="res_model">res.partner.update.from.padron.wizard</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>
    <menuitem action="action_base_partner_update_from_padron" groups="base.group_system" id="menu_base_partner_update_from_padron" parent="contacts.res_partner_menu_config"/>
    <record id="view_base_partner_update_from_padron_form" model="ir.ui.view">
        <field name="name">res.partner.update.from.padron.wizard.form</field>
        <field name="model">res.partner.update.from.padron.wizard</field>
        <field name="arch" type="xml">
            <form string="Actualizar datos desde el padrón AFIP">
                <field invisible="1" name="state"/>
                <header/>
                <sheet>
                    <group invisible="state != 'finished'" col="1">
                        <h2>No hay más contactos que actualizar para esta solicitud...</h2>
                    </group>
                    <p invisible="state != 'option'" class="oe_grey">Solo los contactos con cuit serán actualizados.
                        <br/>
                        Seleccione la lista de campos que desea actualizar.</p>
                    <group invisible="state not in ('option',)">
                        <field name="field_to_update_ids" options="{'no_create': True}" widget="many2many_tags"/>
                        <field name="update_constancia"/>
                        <field name="title_case"/>
                    </group>
                    <group invisible="state in ('option', 'finished')" col="1">
                        <h1>
                            <field required="state == 'selection'" name="partner_id" options="{'no_open': True}"/>
                        </h1>
                        <span>
                            <field name="field_ids" nolabel="1">
                                <list create="false" editable="top">
                                    <field name="field"/>
                                    <field readonly="True" name="old_value"/>
                                    <field name="new_value"/>
                                </list>
                            </field>
                        </span>
                    </group>
                </sheet>
                <footer>
                    <button invisible="state in ('option', 'finished')" class="oe_highlight" name="update_selection" string="Actualizar contacto" type="object"/>
                    <button invisible="state != 'selection'" class="oe_link" name="next_cb" string="Saltar este contacto" type="object"/>
                    <button invisible="state != 'option'" class="oe_highlight" name="start_process_cb" string="Actualización con comprobación manual" type="object"/>
                    <button invisible="state != 'option'" class="oe_highlight" confirm="¿Estás seguro de ejecutar la actualización automática de tus contactos?" name="automatic_process_cb" string="Actualizar automáticamente" type="object"/>
                    <span invisible="state == 'finished'" class="or_cancel">or
                        <button class="oe_link oe_inline" special="cancel" string="Cancelar"/></span>
                    <span invisible="state != 'finished'" class="or_cancel">
                        <button class="oe_link oe_inline" special="cancel" string="Close"/>
                    </span>
                </footer>
            </form>
        </field>
    </record>
    <record id="action_partner_update" model="ir.actions.act_window">
        <field name="name">Automatic Update from Padron</field>
        <field name="res_model">res.partner.update.from.padron.wizard</field>
        <field name="target">new</field>
        <field name="view_mode">form</field>
    </record>
</odoo>
