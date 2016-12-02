import logging

import sqlalchemy
from paste.deploy.converters import asbool

import ckan.logic as logic
import ckan.logic.schema
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.model as model
import ckan.plugins as plugins
import ckan.lib.plugins as lib_plugins

from ckan.logic.action.get import _add_tracking_summary_to_resource_dict

from ckan.common import _

log = logging.getLogger('ckan.logic')

# Define some shortcuts
# Ensure they are module-private so that they don't get loaded as available
# actions in the action API.
_check_access = logic.check_access
_get_or_bust = logic.get_or_bust
_or_ = sqlalchemy.or_


def package_show(context, data_dict):
    """Return the metadata of a dataset (package) and its resources.

    IMPORTANT: This monkeypatches ckan core's `package_show` method, and bypasses
    the `use_cache` part of that function. It was disabled for some reason, and
    needs testing before switching it back on.

    :param id: the id or name of the dataset
    :type id: string
    :param use_default_schema: use default package schema instead of
        a custom schema defined with an IDatasetForm plugin (default: False)
    :type use_default_schema: bool
    :param include_tracking: add tracking information to dataset and
        resources (default: False)
    :type include_tracking: bool
    :rtype: dictionary
    """

    model = context['model']
    context['session'] = model.Session
    name_or_id = data_dict.get("id") or _get_or_bust(data_dict, 'name_or_id')

    pkg = model.Package.get(name_or_id)

    if pkg is None:
        raise logic.NotFound

    context['package'] = pkg

    _check_access('package_show', context, data_dict)

    if data_dict.get('use_default_schema', False):
        context['schema'] = ckan.logic.schema.default_show_package_schema()
    include_tracking = asbool(data_dict.get('include_tracking', False))

    package_dict = None

    if not package_dict:
        package_dict = model_dictize.package_dictize(pkg, context)
        package_dict_validated = False

    if include_tracking:
        # page-view tracking summary data
        package_dict['tracking_summary'] = (
            model.TrackingSummary.get_for_package(package_dict['id']))
        for resource_dict in package_dict['resources']:
            _add_tracking_summary_to_resource_dict(resource_dict, model)

    if context.get('for_view'):
        for item in plugins.PluginImplementations(plugins.IPackageController):
            package_dict = item.before_view(package_dict)

    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.read(pkg)

    for item in plugins.PluginImplementations(plugins.IResourceController):
        for resource_dict in package_dict['resources']:
            item.before_show(resource_dict)

    if not package_dict_validated:
        package_plugin = lib_plugins.lookup_package_plugin(
            package_dict['type'])
        if 'schema' in context:
            schema = context['schema']
        else:
            schema = package_plugin.show_package_schema()
        if schema and context.get('validate', True):
            package_dict, errors = lib_plugins.plugin_validate(
                package_plugin, context, package_dict, schema,
                'package_show')
    for item in plugins.PluginImplementations(plugins.IPackageController):
        item.after_show(context, package_dict)

    return package_dict
