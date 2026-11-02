from odoo import _
from odoo.exceptions import AccessError, ValidationError


def check_domain_fields(target, domain):
    """Do not let configured filters infer values of group-restricted fields."""
    metadata = {}
    for term in domain:
        if not isinstance(term, (list, tuple)) or len(term) != 3 or not isinstance(term[0], str):
            continue
        current = target
        parts = term[0].split('.')
        for index, name in enumerate(parts):
            if current._name not in metadata:
                current.check_access('read')
                metadata[current._name] = current.fields_get()
            if name not in metadata[current._name]:
                raise AccessError(_('A dashboard filter refers to an unavailable or restricted field.'))
            if index < len(parts)-1:
                field = current._fields[name]
                if not field.relational or not field.comodel_name:
                    raise ValidationError(_('Invalid relational field path in a dashboard filter.'))
                current = current.env[field.comodel_name]
