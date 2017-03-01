from logging import getLogger
from string import Template
import json

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

    '''
    License meta data is often inconsistent, this funtion attempts to match known
    license meta data with a list of known Creative Commons URLs and Titles.
    We may update this function over time to help cater for poor quality meta data
    (we should also talk to the agency to get them to improve the quality of their metadata too).

    Should check for:
        CC url returns a 200 response and the reponse URL matches the harvested license property
        CC title in/is harvested license title
        CC title in/is harvested license description
        CC url in/is harvested license description
        CC url is the harvested license link
    '''
    def _fetch_license_id(self, license_url):
        # if a license is not provided we need to return this as other ie. copyright
        if license_url == "":
            return "other"

        licenses = license_list({'model': model}, {})
        try:
            resp = requests.get(license_url)
        except Exception as e:
            log.exception("Failed to get on license url: {}".format(license_url))
            return None
        #dealing with direct CC url don't call for a json response
        try:
            if "https://creativecommons.org" in license_url:
                for license in licenses:
                    if license['url'] == resp.url and resp.status_code == 200:
                        log.debug("Using license {}".format(license['id']))
                        return license['id']
        except Exception as e:
            log.exception("Not a direct CC license URL")

        #not a CC url, call out for json response and check for known variations
        try:
            license_data = resp.json()
            for license in licenses:
                if license['title'] in license_data.get('title', '') or \
                    license['title'] in license_data.get('description', '') or \
                    license['url'] in license_data.get('description', '') or \
                    license['url'] == license_data.get('link', ''):
                        log.debug("Using license {}".format(license['id']))
                        return license['id']
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

    def modify_package_dict(self, package_dict, dcat_dict, harvest_object):
        try:
            conf = json.loads(harvest_object.source.config)
        except ValueError:
            # Failed to decode a JSON object
            log.info("Failed to decode source config, using defaults")
            conf = {}

        tags = package_dict.get('tags', [])
        tags.extend(conf.get('default_tags', []))
        package_dict['tags'] = dict((tag['name'], tag) for tag in tags).values()

        log.error(harvest_object.source.config)

        context = {'model': model, 'user': plugins.toolkit.c.user}
        groups = []
        for group_name_or_id in conf.get('default_groups', []):
            try:
                group = plugins.toolkit.get_action('group_show')(context, {'id': group_name_or_id})
                groups.append({'id': group['id'], 'name': group['name']})
            except plugins.toolkit.ObjectNotFound, e:
                log.error('Default group %s not found, proceeding without.' % group_name_or_id)
                pass

        package_dict['groups'] = dict((group['name'], group) for group in groups).values()
        return package_dict
