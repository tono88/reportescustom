# -*- coding: utf-8 -*-

from odoo import SUPERUSER_ID, api

MODULE = "pos_multi_warehouse_sales_report"
MENU_XMLID = "menu_pos_warehouse_sales_report"
ACTION_XMLID = "action_pos_warehouse_sales_report_wizard"


def _get_action(env):
    return env.ref(f"{MODULE}.{ACTION_XMLID}", raise_if_not_found=False)


def _get_groups(env):
    groups = env["res.groups"]
    for xmlid in ("point_of_sale.group_pos_user", "point_of_sale.group_pos_manager"):
        group = env.ref(xmlid, raise_if_not_found=False)
        if group:
            groups |= group
    return groups


def _find_orders_parent_menu(env):
    """Find the POS > Orders parent menu without depending on translated names."""
    Menu = env["ir.ui.menu"].sudo().with_context(lang=None)

    # 1) Best option: find the menu whose action opens pos.order and use its parent.
    for menu in Menu.search([], order="sequence,id"):
        action = menu.action
        if action and action._name == "ir.actions.act_window" and getattr(action, "res_model", False) == "pos.order":
            return menu.parent_id or menu

    # 2) Common XML IDs seen across Odoo versions/builds.
    candidates = (
        "point_of_sale.menu_point_root",
        "point_of_sale.menu_point_of_sale",
        "point_of_sale.menu_pos_root",
        "point_of_sale.menu_pos_config",
    )
    for xmlid in candidates:
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu:
            return menu

    return Menu.browse()


def _get_existing_menu(env):
    imd = env["ir.model.data"].sudo().search([
        ("module", "=", MODULE),
        ("name", "=", MENU_XMLID),
        ("model", "=", "ir.ui.menu"),
    ], limit=1)
    if imd:
        return env["ir.ui.menu"].sudo().browse(imd.res_id).exists()
    return env["ir.ui.menu"]


def _ensure_xmlid(env, menu):
    imd = env["ir.model.data"].sudo().search([
        ("module", "=", MODULE),
        ("name", "=", MENU_XMLID),
    ], limit=1)
    vals = {"model": "ir.ui.menu", "res_id": menu.id, "noupdate": False}
    if imd:
        imd.write(vals)
    else:
        env["ir.model.data"].sudo().create({
            "module": MODULE,
            "name": MENU_XMLID,
            **vals,
        })


def _create_or_update_menu(env):
    action = _get_action(env)
    if not action:
        return

    parent = _find_orders_parent_menu(env)
    groups = _get_groups(env)
    menu = _get_existing_menu(env)

    values = {
        "name": "Ventas por almacén",
        "parent_id": parent.id if parent else False,
        "action": f"ir.actions.act_window,{action.id}",
        "sequence": 45,
        "groups_id": [(6, 0, groups.ids)],
    }

    if menu:
        menu.write(values)
    else:
        menu = env["ir.ui.menu"].sudo().create(values)
    _ensure_xmlid(env, menu)


def _build_env(cr_or_env, registry=None):
    # Official Odoo 18 hook signature is (cr, registry). Some community
    # examples use env, so this keeps the module tolerant in both cases.
    if hasattr(cr_or_env, "cr") and hasattr(cr_or_env, "uid"):
        return cr_or_env
    return api.Environment(cr_or_env, SUPERUSER_ID, {})


def post_init_hook(cr, registry=None):
    env = _build_env(cr, registry)
    env["pos.warehouse.sales.report.wizard"]._ensure_pos_warehouse_sales_report_menu()


def uninstall_hook(cr, registry=None):
    env = _build_env(cr, registry)
    menu = _get_existing_menu(env)
    if menu:
        menu.unlink()
