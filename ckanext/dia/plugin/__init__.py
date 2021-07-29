# encoding: utf-8
from logging import getLogger

import ckan.plugins as p
from ckan import logic

from ckanext.dia import validators, schema, converters
from ckanext.dia.action import get

if p.toolkit.check_ckan_version(min_version='2.9.0'):
    from ckanext.dia.plugin.flask_plugin import (
        DIANoHomepageMixin, DIACommandsMixin
    )
else:
    from ckanext.dia.plugin.pylons_plugin import (
        DIANoHomepageMixin, DIACommandsMixin
    )

log = getLogger(__name__)


class DIAValidationPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IValidators)


    def update_config(self, config):
        # monkeypatching validators
        logic.validators.isodate = validators.isodate
        logic.validators.extra_key_not_in_root_schema = validators.extra_key_not_in_root_schema

    def get_validators(self):
        return {
            'force_lower': validators.force_lower,
            'natural_num_or_missing': validators.natural_num_or_missing,
            'fix_code_style_list': converters.fix_code_style_list
        }


class DIASchemaPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)

    def update_config(self, config):
        # monkeypatching default_extras_schema to add `theme` key.
        logic.schema.default_extras_schema = schema.default_extras_schema


class DIAActionsPlugin(p.SingletonPlugin):
    p.implements(p.IActions)

    def get_actions(self):
        return {'package_show': get.package_show}


class DIANoHomepagePlugin(DIANoHomepageMixin, p.SingletonPlugin):
    """
    Redirect / to /dataset

    Homepage for catalog will be handled on CWP/Silverstripe site
    """
    pass

class DIACommandsPlugin(DIACommandsMixin, p.SingletonPlugin):
    pass
