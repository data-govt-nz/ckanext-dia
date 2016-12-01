# encoding: utf-8

import ckan.plugins as plugins

from ckanext.dia import validators


class DIAValidationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self):
        return {
            'natural_num_or_missing': validators.natural_num_or_missing,
            'isodate': validators.isodate,
            'extra_key_not_in_root_schema': validators.extra_key_not_in_root_schema
        }
