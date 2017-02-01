# encoding: utf-8
from logging import getLogger

import ckan.plugins as plugins
import ckan.logic.schema
import ckan.logic.validators

from ckanext.dia import validators, schema, converters
from ckanext.dia.action import get

log = getLogger(__name__)


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


class DIANoHomepagePlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IRoutes, inherit=True)

    def before_map(self, m):
        """
        Redirect / to /dataset

        Homepage for catalog will be handled on CWP/Silverstrip site
        """
        # This would be better as plugins.toolkit.url_for(..) but for some reason
        # url_for(controller='package', action='search') return /user/edit/
        # Possibly something todo with import order?
        m.redirect('/', '/dataset')
        return m
