from logging import getLogger
from string import Template

import requests

from ckan import model
import ckan.plugins as plugins
from ckan.logic.action.get import license_list
from ckanext.dcat.harvesters import DCATJSONHarvester

log = getLogger(__name__)


class DIADCATJSONHarvester(DCATJSONHarvester):

    extent_template = Template('''
    {"type": "Polygon", "coordinates": [[[$xmin, $ymin], [$xmax, $ymin], [$xmax, $ymax], [$xmin, $ymax], [$xmin, $ymin]]]}
    ''')

    def _clean_email(self, email):
        if email.startswith("mailto:"):
            email = email[7:]
        return email

    def _clean_spatial(self, spatial):
        # Convert things like "173.0039,-42.3167,174.2099,-41.0717" to
        # Polygon using templates from CSW
        xmin, ymin, xmax, ymax = spatial.split(',')
        return self.extent_template.substitute(
            xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax
        ).strip()

    def _normalize_licence(self, licence):
        """
        Noone can agree on the spelling of license in their description, so we have to normalize
        """
        return licence.lower().replace('licence', 'license')

    def _fetch_license_id(self, license_url):
        licenses = license_list({'model': model}, {})
        try:
            resp = requests.get(license_url)
            resp.raise_for_status()
            license_data = resp.json()
            for lics in licenses:  # 'license' is a global. TIL
                if self._normalize_licence(lics['title']) == self._normalize_licence(license_data.get('title', '')) or \
                   self._normalize_licence(lics['title']) == self._normalize_licence(license_data.get('description', '')) or \
                   lics['url'] == license_data.get('link', ''):
                    log.debug("Using license {}".format(lics['id']))
                    return lics['id']
        except Exception as e:
            log.exception("Failed to retrieve license data")
            return None

    def _get_package_dict(self, harvest_object):
        package_dict, dcat_dict = super(DIADCATJSONHarvester, self)._get_package_dict(harvest_object)

        mappings = {
            'issued': lambda x: x['issued'],
            'modified': lambda x: x['modified'],
            'author': lambda x: x['publisher']['name'],
            'maintainer': lambda x: x['contactPoint']['fn'],
            'maintainer_email': lambda x: self._clean_email(x['contactPoint']['hasEmail']),
            'maintainer_phone': lambda x: x['contactPoint']['hasTelephone'],
            'theme': lambda x: x['theme'][0],
            'rights': lambda x: x['rights'],  # Not tested
            'frequency_of_update': lambda x: x['accrualPeriodicity'],  # Not tested
            'spatial': lambda x: self._clean_spatial(x['spatial']),
            'language': lambda x: x['language'],
            'source_identifier': lambda x: x['identifier'],
            'license_url': lambda x: x['license'],
            'license_id': lambda x: self._fetch_license_id(x['license'])
        }

        for k, v in mappings.items():
            try:
                package_dict[k] = v(dcat_dict)
            except KeyError, IndexError:
                pass

        log.debug("DCAT package_dict: {}".format(package_dict))
        log.debug("DCAT dcat_dict: {}".format(dcat_dict))

        return package_dict, dcat_dict
