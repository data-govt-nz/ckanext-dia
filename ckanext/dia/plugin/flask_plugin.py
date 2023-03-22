# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckanext.dia.cli as cli
import ckanext.dia.views as views


class DIACommandsMixin(p.SingletonPlugin):
    p.implements(p.IClick)

    # IClick

    def get_commands(self):
        return cli.get_commands()


class DIANoHomepageMixin(p.SingletonPlugin):
    p.implements(p.IBlueprint)

    # IBlueprint

    def get_blueprint(self):
        return views.no_home_page
