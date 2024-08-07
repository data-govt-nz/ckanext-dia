from __future__ import absolute_import
import six
from logging import getLogger
from string import Template
import json
import traceback
import re
from urllib.parse import urlparse

import requests

from ckan import model
import ckan.plugins as p
import ckan.plugins.toolkit as tk
from ckan.logic.action.get import license_list
from ckanext.dcat.harvesters import DCATJSONHarvester
from ckanext.dcat.interfaces import IDCATRDFHarvester
from ckanext.dia.converters import strip_invalid_tags_content
from ckanext.dia.harvester.clean_frequency import clean_frequency

log = getLogger(__name__)


class DIADCATJSONHarvester(DCATJSONHarvester):
    p.implements(IDCATRDFHarvester, inherit=True)

    extent_template = Template('''
        {
            "type": "Polygon",
            "coordinates": [
                [
                    [$xmin, $ymin],
                    [$xmax, $ymin],
                    [$xmax, $ymax],
                    [$xmin, $ymax],
                    [$xmin, $ymin]
                ]
            ]
        }
    ''')

    # IDCATRDFHarvester
    def update_session(self, session):
        session.headers.update({'X-Harvest': 'data.govt.nz/dcat-json'})
        return session

    def _clean_email(self, email):
        if email.startswith("mailto:"):
            email = email[7:]
        return email

    def _clean_spatial(self, spatial):
        # Convert things like "173.0039,-42.3167,174.2099,-41.0717" to
        # Polygon using templates from CSW
        if isinstance(spatial, six.string_types):
            spatial = spatial.strip()
            if re.match(r'^([\d\-\.]+\,){3}[\d\-\.]+$', spatial):
                xmin, ymin, xmax, ymax = spatial.split(',')

                if xmin == xmax:
                    raise ValueError("Spatial x coordinates are the same.")
                if ymin == ymax:
                    raise ValueError("Spatial y coordinates are the same.")

                return self.extent_template.substitute(
                    xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax
                ).strip()
            else:
                raise ValueError("Invalid spatial data.")
        elif isinstance(spatial, dict):
            return json.dumps(spatial)
        else:
            return spatial

    '''
    License meta data is often inconsistent, this funtion attempts to match
    known license meta data with a list of known Creative Commons URLs and
    Titles. We may update this function over time to help cater for poor
    quality meta data (we should also talk to the agency to get them to
    improve the quality of their metadata too).

    Should check for:
        CC url returns a 200 response and the reponse URL matches the
            harvested license property
        CC title in/is harvested license title
        CC title in/is harvested license description
        CC url in/is harvested license description
        CC url is the harvested license link
    '''

    def _fetch_license_id(self, license_url, harvest_object):
        # if a license is not provided we need to return this as
        # other ie. copyright
        if license_url == "":
            return "other"

        licenses = license_list({'model': model}, {})
        try:
            resp = requests.get(license_url)
        except (requests.exceptions.InvalidSchema,
                requests.exceptions.InvalidURL,
                requests.exceptions.MissingSchema):
            self._save_object_error(
                f'License URL is invalid.',
                harvest_object)
            return None
        except Exception as e:
            log.exception("Failed to fetch license.")
            self._save_object_error(
                f"Fetching license at '{license_url}' failed: {e}",
                harvest_object)
            return None
        # dealing with direct CC url don't call for a json response
        try:
            if urlparse(license_url).netloc == 'creativecommons.org':
                for license in licenses:
                    if (urlparse(license['url'])._replace(scheme='http') ==
                       urlparse(resp.url)._replace(scheme='http') and resp.status_code == 200):
                        log.debug("Using license {}".format(license['id']))
                        return license['id']
        except Exception:
            log.exception("Not a direct CC license URL")

        # not a CC url, call out for json response and
        # check for known variations
        try:
            license_data = resp.json()
            for license in licenses:
                can_use_license = (
                    license['title'] in license_data.get('title', '') or
                    license['title'] in license_data.get('description', '') or
                    license['url'] in license_data.get('description', '') or
                    license['url'] == license_data.get('link', '')
                )
                if can_use_license:
                    log.debug("Using license {}".format(license['id']))
                    return license['id']
        except Exception:
            self._save_object_error(
                f'Failed to parse license, response not JSON. URL: {license_url}',
                harvest_object)
            return None

    def _get_package_dict(self, harvest_object):
        package_dict, dcat_dict = super(
            DIADCATJSONHarvester, self)._get_package_dict(harvest_object)

        mappings = {
            'issued': lambda x: x['issued'],
            'modified': lambda x: x['modified'],
            'author': lambda x: x['publisher']['name'],
            'maintainer': lambda x: x['contactPoint']['fn'],
            'maintainer_email': lambda x:
                self._clean_email(x['contactPoint']['hasEmail']),
            'maintainer_phone': lambda x: x['contactPoint']['hasTelephone'],
            'theme': lambda x: x['theme'],
            'rights': lambda x: x['rights'],  # Not tested
            'frequency_of_update': lambda x:
                clean_frequency(x['accrualPeriodicity']),
            'language': lambda x: x['language'],
            'source_identifier': lambda x: x['identifier'],
            'license_url': lambda x: x['license'],
            'license_id':
                lambda x: self._fetch_license_id(x['license'], harvest_object),
            'temporal': lambda x: x['temporal']
        }

        for k, v in list(mappings.items()):
            try:
                package_dict[k] = v(dcat_dict)
            except KeyError:
                pass
            except Exception:
                self._save_object_error(
                    f'Failed parsing data on {k}:\n{traceback.format_exc()}',
                    harvest_object)

        if 'spatial' in dcat_dict:
            if dcat_dict.get('spatial') != "":
                try:
                    package_dict['spatial'] = self._clean_spatial(dcat_dict['spatial'])
                except ValueError as e:
                    self._save_object_error(
                        f'Received invalid spatial data: {e}',
                        harvest_object)
            else:
                self._save_object_error(
                    f'Received empty spatial data.',
                    harvest_object)

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
        tags = strip_invalid_tags_content(tags)
        tags.extend(conf.get('default_tags', []))
        package_dict['tags'] = list(dict((tag['name'], tag)
                                    for tag in tags).values())

        context = {'model': model, 'user': self._get_user_name()}
        groups = []

        # DATA-519: Get existing groups from the package
        # before appending default groups
        try:
            query = {'id': package_dict.get('name', None)}
            original_package = tk.get_action(
                'package_show')(context, query)
            groups = original_package['groups']
        except tk.ObjectNotFound:
            pass

        for group_name_or_id in conf.get('default_groups', []):
            try:
                group = tk.get_action('group_show')(
                    context, {'id': group_name_or_id})
                groups.append({'id': group['id'], 'name': group['name']})
            except tk.ObjectNotFound:
                log.error(
                    'Default group %s not found, proceeding without.'
                    % group_name_or_id)
                pass

        package_dict['groups'] = list(
            dict((group['name'], group) for group in groups).values())

        package_theme_is_list = (
            package_dict.get('theme', None) and
            isinstance(package_dict.get('theme'), list)
        )
        if package_theme_is_list:
            package_dict['theme'] = json.dumps(package_dict.get('theme'))

        return package_dict
