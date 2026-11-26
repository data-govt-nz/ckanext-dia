"""Keep resource ids stable across harvest updates (DATA-1485).

ckanext-spatial's import_stage builds a fresh ``resources`` list, without ids,
on every update and passes it to ``package_update``. CKAN then treats every
resource as new: the old ones are soft-deleted and replaced, so each harvest
leaves behind a deleted resource row and (via ckanext-xloader) an orphaned
DataStore table, and the replacement gets a new, empty table. Copying the ids
of the matching existing resources across means ``package_update`` updates
them in place, and xloader truncates and reloads the table it already has.
"""
from logging import getLogger

log = getLogger(__name__)

# Most specific first. Each existing resource is only matched once.
_IDENTITY_FUNCTIONS = (
    lambda r: (r.get('url'), r.get('name'), r.get('format')),
    lambda r: (r.get('url'), r.get('name')),
    lambda r: r.get('url'),
)


def copy_resource_ids(existing_resources, new_resources):
    """Set 'id' on each of new_resources that matches an existing resource.

    Matches on url, name and format, then url and name, then url alone.
    A new resource that already has an id is left alone, and each existing
    resource is matched at most once. Modifies new_resources in place and
    returns the number of ids copied.
    """
    unmatched = [r for r in existing_resources if r.get('id')]
    pending = [r for r in new_resources if not r.get('id') and r.get('url')]
    copied = 0

    for identity in _IDENTITY_FUNCTIONS:
        if not unmatched or not pending:
            break
        for resource in list(pending):
            key = identity(resource)
            for existing in unmatched:
                if identity(existing) == key:
                    resource['id'] = existing['id']
                    unmatched.remove(existing)
                    pending.remove(resource)
                    copied += 1
                    break
    return copied


def copy_resource_ids_from_package(package_id, package_dict):
    """Carry over resource ids from the existing dataset ``package_id``.

    Does nothing for a dataset that doesn't exist yet (a 'new' harvest object
    has no package_id).
    """
    if not package_id or not package_dict.get('resources'):
        return

    from ckan import model
    import ckan.plugins.toolkit as tk

    try:
        existing = tk.get_action('package_show')(
            {'model': model, 'ignore_auth': True, 'for_update': True},
            {'id': package_id})
    except tk.ObjectNotFound:
        return

    copied = copy_resource_ids(existing.get('resources', []),
                               package_dict['resources'])
    log.debug('Kept %d of %d resource ids for dataset %s',
              copied, len(package_dict['resources']), package_id)
