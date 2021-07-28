# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckanext.dia.cli as cli
import ckanext.dia.views as views


class DIANoHomepageMixin(p.SingletonPlugin):
    p.implements(p.IBlueprint)

    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprints()
