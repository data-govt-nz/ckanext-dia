
# -*- coding: utf-8 -*-

import ckan.plugins as p

class DIANoHomepageMixin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # IRoutes

    def before_map(self, map):
        """
        Redirect / to /dataset

        Homepage for catalog will be handled on CWP/Silverstripe site
        """
        map.redirect('/', '/dataset')
        return map
