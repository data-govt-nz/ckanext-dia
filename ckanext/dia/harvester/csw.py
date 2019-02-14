import json
import pycountry
from logging import getLogger

from ckan import model
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
                country = pycountry.countries.get(alpha_3=dia_values['jurisdiction'].upper())
                if country:
                    dia_values['jurisdiction'] = country.name
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
            except (KeyError, IndexError):
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
            except (KeyError, IndexError):
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

            data_format = dia_values['data-format']
            if len(data_format) != 0:
                resource['format'] = _filter_format(data_format[0]['name'])

        try:
            package_dict['frequency_of_update'] = _get_object_extra(package_dict, 'frequency-of-update')
        except KeyError:
            pass

        log.debug("CSW iso_values: {}".format(iso_values))
        log.debug("CSW package_dict: {}".format(package_dict))
        log.debug("CSW custom mappings: {}".format(dia_values))

        # Adding default tags and groups from the source config
        try:
            conf = json.loads(data_dict['harvest_object'].source.config)
        except ValueError:
            # Failed to decode a JSON object
            log.info("Failed to decode source config, using defaults")
            conf = {}

        tags = package_dict.get('tags', [])
        tags.extend(conf.get('default_tags', []))
        package_dict['tags'] = dict((tag['name'], tag) for tag in tags).values()

        # Adding default_groups from config. This was previously not supported
        # by ckanext-spatial.
        context = {'model': model, 'user': plugins.toolkit.c.user}
        groups = []
        for group_name_or_id in conf.get('default_groups', []):
            try:
                group = plugins.toolkit.get_action('group_show')(context, {'id': group_name_or_id})
                groups.append({'id': group['id'], 'name': group['name']})
            except plugins.toolkit.ObjectNotFound, e:
                logging.error('Default group %s not found, proceeding without.' % group_name_or_id)
                pass

        package_dict['groups'] =  dict((group['id'], group) for group in groups).values()

        # CSW records can have a non wgs-84 projection, we will need to convert the geojson to wgs-84
        for extra in package_dict['extras']:
            if extra['key'] == 'spatial-reference-system':
                spatial_srid = extra['value']
            if extra['key'] == 'spatial':
                try:
                    spatial_geojson = json.loads(extra['value'])
                except ValueError:
                    log.warn('Failed to parse json for spatial field of package {}'.format(package_dict))

        if not not spatial_srid and spatial_geojson is not None:
            from pyproj import Proj, transform

            outProj = Proj('+init=EPSG:4326')
            inProj = Proj('+init=EPSG:' + spatial_srid)

            if spatial_geojson['type'] == 'MultiPolygon':
                new_polygons = []
                for polygon in spatial_geojson['coordinates']:
                    new_linestrings = []
                    for linestring in polygon:
                        new_linestring = []
                        for x,y in linestring:
                            nx, ny = transform(inProj, outProj, x, y)
                            new_linestring.append([nx, ny])
                        new_linestrings.append(new_linestring)
                    new_polygons.append(new_linestrings)
                spatial_geojson['coordinates'] = new_polygons

            elif spatial_geojson['type'] == 'Polygon':
                new_linestrings = []
                for linestring in spatial_geojson['coordinates']:
                    new_linestring = []
                    for x,y in linestring:
                        nx, ny = transform(inProj, outProj, x, y)
                        new_linestring.append([nx, ny])
                    new_linestrings.append(new_linestring)
                spatial_geojson['coordinates'] = new_linestrings

            elif spatial_geojson['type'] == 'Point':
                # {"type": "Point", "coordinates": [2145000.0, 5467000.0]}'}
                x,y = spatial_geojson['coordinates']
                nx, ny = transform(inProj, outProj, x, y)
                spatial_geojson['coordinates'] = [nx, ny]
            else:
                msg = 'The DIA CSW harvest does not understand how to re-project a {} type of geojson'
                log.warn(msg.format(spatial_geojson['spatial']))

            # create updated version of extras array with correct SRID + spatial field
            new_extras = []
            for extra in package_dict['extras']:
                if extra['key'] == 'spatial':
                    new_extras.append({'key': 'spatial', 'value': json.dumps(spatial_geojson)})
                elif extra['key'] == 'spatial-reference-system':
                    new_extras.append({'key': 'spatial-reference-system', 'value': '4326'})
                else:
                    new_extras.append(extra)
            package_dict['extras'] = new_extras
        else:
            log.warning('Could not determine SRID or spatial field for package {}'.format(package_dict))

        return package_dict


def _filter_rights(dia_values):
    # Pull out 'use_limitation' for the first item that has 'use_constraints' set to
    # copyright or intellectualPropertyRights
    # If we raise a KeyError or IndexError, the item is skipped - which is what we want
    # if we can't find the value we want
    candidates = [x for x in dia_values['rights'] if x['use_constraints'] in ('copyright', 'intellectualPropertyRights')]
    return candidates[0]['use_limitation']


def _filter_format(format_str):
    return format_str[2:] if format_str.startswith("*.") else format_str


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
