# encoding: utf-8

import ckan.plugins as plugins

from ckanext.dia.validators import natural_num_or_missing


class DIAValidationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self):
        return {'natural_num_or_missing': natural_num_or_missing}
