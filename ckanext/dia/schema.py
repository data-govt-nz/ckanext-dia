from ckan.lib.navl.validators import ignore_missing, not_empty, ignore, not_missing


def default_extras_schema():
    return {
        'id': [ignore],
        'key': [not_empty, unicode],
        'value': [not_missing],
        'state': [ignore],
        'deleted': [ignore_missing],
        'revision_timestamp': [ignore],
        '__extras': [ignore],
        'theme': [ignore],
    }
