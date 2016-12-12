# encoding: utf-8

import ckan.plugins as plugins
import ckan.logic.schema
import ckan.logic.validators

from ckanext.dia import validators, schema, converters
from ckanext.dia.action import get

from ckanext.spatial.interfaces import ISpatialHarvester


class DIAValidationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators)

    def update_config(self, config):
        # monkeypatching isodate and extra_key_not_in_root_schema validators
        ckan.logic.validators.isodate = validators.isodate
        ckan.logic.validators.extra_key_not_in_root_schema = validators.extra_key_not_in_root_schema

    def get_validators(self):
        return {
            'force_lower': validators.force_lower,
            'natural_num_or_missing': validators.natural_num_or_missing,
            'fix_code_style_list': converters.fix_code_style_list
        }


class DIASchemaPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)

    def update_config(self, config):
        # monkeypatching default_extras_schema to add `theme` key.
        ckan.logic.schema.default_extras_schema = schema.default_extras_schema


class DIAActionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IActions)

    def get_actions(self):
        return {'package_show': get.package_show}


class DIASpatialHarvester(plugins.SingletonPlugin):
    plugins.implements(ISpatialHarvester, inherit=True)

    def get_package_dict(self, context, data_dict):

        package_dict = data_dict['package_dict']
        iso_values = data_dict['iso_values']

        package_issued = iso_values['date-released']
        package_modified = iso_values['date-updated']

        package_dict['issued'] = package_issued
        package_dict['modified'] = package_modified

        # Override resource name, set it to package title if unset
        RESOURCE_NAME_CKAN_DEFAULT = plugins.toolkit._('Unnamed resource')
        package_title = package_dict.get('title', RESOURCE_NAME_CKAN_DEFAULT)
        for resource in package_dict['resources']:
            if resource['name'] == RESOURCE_NAME_CKAN_DEFAULT:
                resource['name'] = package_title

            # Set resouce_created and last_modified on resources to be
            # date-released and date-updated from the dataset respectively
            resource['resource_created'] = package_issued
            resource['last_modified'] = package_modified

        return package_dict
