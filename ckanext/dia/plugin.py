# encoding: utf-8
from logging import getLogger
from string import Template

import pycountry
import requests

import ckan.plugins as plugins
import ckan.logic.schema
import ckan.logic.validators
from ckan.logic.action.get import license_list
from ckan import model

from ckanext.spatial.interfaces import ISpatialHarvester
from ckanext.dcat.harvesters import DCATJSONHarvester

from ckanext.dia import validators, schema, converters
from ckanext.dia.action import get
from .harvester import DIADocument

log = getLogger(__name__)


class DIAValidationPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IValidators)

    def update_config(self, config):
        # monkeypatching isodate and extra_key_not_in_root_schema validators
        ckan.logic.validators.isodate = validators.isodate

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


class DIASpatialHarvester(plugins.SingletonPlugin):
    plugins.implements(ISpatialHarvester, inherit=True)

    def get_package_dict(self, context, data_dict):

        package_dict = data_dict['package_dict']
        iso_values = data_dict['iso_values']

        dia_values = DIADocument(data_dict['harvest_object'].content).read_values()

        if 'language' in dia_values:
            try:
                dia_values['language'] = pycountry.languages.get(alpha_3=dia_values['language']).name
            except KeyError:
                pass

        if 'jurisdiction' in dia_values:
            try:
                dia_values['jurisdiction'] = pycountry.countries.get(alpha_3=dia_values['jurisdiction'].upper()).name
            except KeyError:
                pass

        dia_mappings = {
            'language': lambda x: x['language'],
            'jurisdiction': lambda x: x['jurisdiction'],
            'maintainer_phone': lambda x: x['metadata-point-of-contact'][0]['contact-info']['phone'],
            'rights': _filter_rights
        }

        for k, v in dia_mappings.items():
            try:
                package_dict[k] = v(dia_values)
            except KeyError, IndexError:
                pass

        package_issued = iso_values['date-released']
        package_modified = iso_values['date-updated']

        package_dict['issued'] = package_issued
        package_dict['created'] = package_issued

        package_dict['modified'] = package_modified
        package_dict['last_modified'] = package_modified

        iso_mappings = {
            'author': lambda x: x['metadata-point-of-contact'][0]['organisation-name'],
            'maintainer': lambda x: x['metadata-point-of-contact'][0]['position-name'],
            'maintainer_email': lambda x: x['metadata-point-of-contact'][0]['contact-info']['email']
        }

        for k, v in iso_mappings.items():
            try:
                package_dict[k] = v(iso_values)
            except KeyError, IndexError:
                pass

        # Override resource name, set it to package title if unset
        RESOURCE_NAME_CKAN_DEFAULT = plugins.toolkit._('Unnamed resource')
        package_title = package_dict.get('title', RESOURCE_NAME_CKAN_DEFAULT)
        for resource in package_dict['resources']:
            if resource['name'] == RESOURCE_NAME_CKAN_DEFAULT:
                resource['name'] = package_title

            # Set resouce_created and last_modified on resources to be
            # date-released and date-updated from the dataset respectively
            resource['resource_created'] = package_issued
            resource['last_modified'] = package_modified

        try:
            package_dict['frequency_of_update'] = _get_object_extra(package_dict, 'frequency-of-update')
        except KeyError:
            pass

        log.debug("CSW iso_values: {}".format(iso_values))
        log.debug("CSW package_dict: {}".format(package_dict))

        return package_dict


def _filter_rights(dia_values):
    # Pull out 'use_limitation' for the first item that has 'use_constraints' set to
    # copyright or intellectualPropertyRights
    # If we raise a KeyError or IndexError, the item is skipped - which is what we want
    # if we can't find the value we want
    candidates = [x for x in dia_values['rights'] if x['use_constraints'] in ('copyright', 'intellectualPropertyRights')]
    return candidates[0]['use_limitation']


def _get_object_extra(harvest_object, key):
    '''
    Helper function for retrieving the value from a harvest object extra,
    given the key
    From ckanext.spatial.harvesters.base
    '''
    for extra in harvest_object['extras']:
        if extra['key'] == key:
            return extra['value']
    raise KeyError(key)


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
