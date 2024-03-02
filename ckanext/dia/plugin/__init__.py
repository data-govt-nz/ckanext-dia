# encoding: utf-8
from logging import getLogger

import ckan.plugins as p
from ckan.plugins import toolkit as tk
from ckan import logic

from ckanext.dia import schema, converters, views
from ckanext.dia.validators import (
    isodate, extra_key_not_in_root_schema,
    force_lower, natural_num_or_missing
)
from ckanext.dia.model import define_table

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
    p.implements(p.IValidators)

    def get_validators(self):
        return {
            'isodate': isodate,
            'extra_key_not_in_root_schema': extra_key_not_in_root_schema,
            'force_lower': force_lower,
            'natural_num_or_missing': natural_num_or_missing,
            'fix_code_style_list': converters.fix_code_style_list
        }


class DIASchemaPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)

    def update_config(self, config):
        # monkeypatching default_extras_schema to add `theme` key.
        logic.schema.default_extras_schema = schema.default_extras_schema


class DIAUriMintingPlugin(p.SingletonPlugin):
    p.implements(p.IConfigurer)
    p.implements(p.IBlueprint)

    # IBlueprint

    def get_blueprint(self):
        return views.uri_minter

    # IConfigurer

    def update_config(self, config):
        define_table()

        tk.add_template_directory(config, '../templates')


class DIANoHomepagePlugin(DIANoHomepageMixin, p.SingletonPlugin):
    """
    Redirect / to /dataset

    Homepage for catalog will be handled on CWP/Silverstripe site
    """
    pass


class DIACommandsPlugin(DIACommandsMixin, p.SingletonPlugin):
    pass
