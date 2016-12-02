# encoding: utf-8

import ckan.plugins as plugins
import ckan.logic.schema

from ckanext.dia import validators, schema
from ckanext.dia.action import get


class DIAValidationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self):
        return {
            'force_lower': validators.force_lower,
            'natural_num_or_missing': validators.natural_num_or_missing,
            'isodate': validators.isodate,
            'extra_key_not_in_root_schema': validators.extra_key_not_in_root_schema
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
