
# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

MEGAPRINT_QWEB = 'l10n_gt_fel_megaprint_report.report_fel_invoice'
DEFAULT_QWEB   = 'account.report_invoice_document'  # fallback

CANDIDATE_REPORT_XMLIDS = [
    'account.action_report_invoice',
    'account.account_invoices',
    'account.action_report_move',
]

def _ensure_env(env_or_cr):
    # Accept either an Environment (new style) or a cursor (legacy)
    if isinstance(env_or_cr, api.Environment):
        return env_or_cr
    cr = env_or_cr
    return api.Environment(cr, SUPERUSER_ID, {})

def _find_invoice_action(env):
    # Prefer known XMLIDs
    for xid in CANDIDATE_REPORT_XMLIDS:
        act = env.ref(xid, raise_if_not_found=False)
        if act and act._name == 'ir.actions.report':
            return act
    # Fallback: first PDF report on account.move
    act = env['ir.actions.report'].search([
        ('model', '=', 'account.move'),
        ('report_type', '=', 'qweb-pdf'),
    ], order='id', limit=1)
    return act or None

def _update_email_template(env, action):
    tmpl = env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
    if not tmpl:
        _logger.warning('No se encontró account.email_template_edi_invoice')
        return
    # Field can be report_template or report_template_id
    fname = 'report_template' if 'report_template' in tmpl._fields else (
            'report_template_id' if 'report_template_id' in tmpl._fields else None)
    if fname:
        tmpl.write({fname: action.id})
        _logger.info('Email de factura ahora adjunta: %s', action.report_name)
    else:
        _logger.warning('El template de email no tiene campo report_template{_id} en esta versión')

def post_init_set_megaprint_invoice(env_or_cr):
    env = _ensure_env(env_or_cr)
    try:
        act = _find_invoice_action(env)
        if not act:
            _logger.error('No se pudo localizar ir.actions.report de factura para reemplazar.')
            return
        act.write({
            'report_name': MEGAPRINT_QWEB,
            'report_file': MEGAPRINT_QWEB,
            'name': 'Factura (Megaprint)',
        })
        _logger.info('Acción de impresión de factura ahora usa: %s', MEGAPRINT_QWEB)
        _update_email_template(env, act)
    except Exception as e:
        _logger.exception('Error configurando Megaprint como reporte por defecto: %s', e)

def uninstall_restore_default_invoice(env_or_cr):
    env = _ensure_env(env_or_cr)
    try:
        act = _find_invoice_action(env)
        if not act:
            return
        default_view = env['ir.ui.view'].search([('key', '=', DEFAULT_QWEB)], limit=1)
        if default_view:
            act.write({
                'report_name': DEFAULT_QWEB,
                'report_file': DEFAULT_QWEB,
                'name': 'Factura',
            })
            _logger.info('Se restauró la acción de factura al template estándar: %s', DEFAULT_QWEB)
        tmpl = env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        if tmpl:
            fname = 'report_template' if 'report_template' in tmpl._fields else (
                    'report_template_id' if 'report_template_id' in tmpl._fields else None)
            if fname:
                std_act = env['ir.actions.report'].search([('report_name', '=', DEFAULT_QWEB)], limit=1)
                if std_act:
                    tmpl.write({fname: std_act.id})
    except Exception as e:
        _logger.exception('Error restaurando configuración por defecto: %s', e)
