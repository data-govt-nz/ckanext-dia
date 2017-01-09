import pycountry
from logging import getLogger

import ckan.plugins as plugins
from ckanext.spatial.interfaces import ISpatialHarvester
from ckanext.spatial.model import MappedXmlDocument, ISOElement, ISODataFormat

log = getLogger(__name__)


class DIAISOResponsibleParty(ISOElement):

    elements = [
        ISOElement(
            name="contact-info",
            search_paths=[
                "gmd:contactInfo/gmd:CI_Contact",
            ],
            multiplicity="0..1",
            elements=[
                ISOElement(
                    name="phone",
                    search_paths=[
                        "gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString/text()",
                    ],
                    multiplicity="0..1",
                ),
            ]
        )
    ]


class DIARights(ISOElement):

    elements = [
        ISOElement(
            name="use_limitation",
            search_paths=[
                "gmd:useLimitation/gco:CharacterString/text()"
            ],
            multiplicity="0..1"
        ),
        ISOElement(
            name="use_constraints",
            search_paths=[
                "gmd:useConstraints/gmd:MD_RestrictionCode/text()"
            ],
            multiplicity="0..1"
        ),
    ]


class DIADocument(MappedXmlDocument):

    elements = [
        ISOElement(
            name="language",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gco:CharacterString/text()",
                # Original search strings from ckanext.spatial.models.harvested_metadata
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/@codeListValue",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:language/gmd:LanguageCode/text()",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:language/gmd:LanguageCode/text()",
            ],
            multiplicity="0..1",
        ),
        ISOElement(
            name="jurisdiction",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicDescription/gmd:geographicIdentifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()"
            ],
            multiplicity="0..1"
        ),
        DIAISOResponsibleParty(
            name="metadata-point-of-contact",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
                "gmd:identificationInfo/srv:SV_ServiceIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty",
            ],
            multiplicity="1..*",
        ),
        DIARights(
            name="rights",
            search_paths=[
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints"
            ],
            multiplicity="*"
        ),
        ISODataFormat(
            name="data-format",
            search_paths=[
                "gmd:distributionInfo/gmd:MD_Distribution/gmd:distributionFormat/gmd:MD_Format",
                "gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceFormat/gmd:MD_Format"
            ],
            multiplicity="*",
        )
    ]


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
            'rights': _filter_rights,
            'format': lambda x: _filter_format(x['data-format'][0]['name'])
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

            resource['format'] = _filter_format(dia_values['data-format'][0]['name'])

        try:
            package_dict['frequency_of_update'] = _get_object_extra(package_dict, 'frequency-of-update')
        except KeyError:
            pass

        log.debug("CSW iso_values: {}".format(iso_values))
        log.debug("CSW package_dict: {}".format(package_dict))
        log.debug("CSW custom mappings: {}".format(dia_values))

        return package_dict


def _filter_rights(dia_values):
    # Pull out 'use_limitation' for the first item that has 'use_constraints' set to
    # copyright or intellectualPropertyRights
    # If we raise a KeyError or IndexError, the item is skipped - which is what we want
    # if we can't find the value we want
    candidates = [x for x in dia_values['rights'] if x['use_constraints'] in ('copyright', 'intellectualPropertyRights')]
    return candidates[0]['use_limitation']


def _filter_format(format_str):
    return format_str[2:] if format_str.startwith("*.") else format_str


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
