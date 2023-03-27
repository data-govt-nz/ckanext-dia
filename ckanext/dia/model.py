# encoding: utf-8

from __future__ import print_function
import datetime
import logging
import sys
import six
from sqlalchemy import Table, Column, types, ForeignKey
from urllib.parse import urljoin, quote
from os.path import join
import uuid

from ckan import model
from ckan.lib.navl.dictization_functions import validate
from ckan.lib.navl.validators import not_empty
from ckan.logic import ValidationError
from ckan.logic.validators import Invalid
from ckan.logic.converters import remove_whitespace
from ckan.model import DomainObject
from ckan.model.meta import metadata, mapper
from ckan.common import _, config


log = logging.getLogger(__name__)
minted_uri_table = None


def db_setup():
    if minted_uri_table is None:
        define_table()

    if not model.package_table.exists():
        log.critical("Exiting: can not migrate minted uri model"
                     "if the database does not exist yet")
        sys.exit(1)
        return

    if not minted_uri_table.exists():
        minted_uri_table.create()
        print("Created Minted URI table")
    else:
        print("Minted URI table already exists -- skipping creation")


def define_table():
    global minted_uri_table
    if minted_uri_table is not None:
        return
    minted_uri_table = Table(
        'minted_uri', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('uri', types.UnicodeText),
        Column('type', types.UnicodeText),
        Column('name', types.UnicodeText),
        Column('created_by_id', types.UnicodeText, ForeignKey('user.id')),
        Column('created_at', types.DateTime, default=datetime.datetime.utcnow))

    mapper(
        MintedURI,
        minted_uri_table
    )


def default_schema():
    schema = {
        'type': [not_empty, six.text_type, remove_whitespace],
        'name': [not_empty, six.text_type, remove_whitespace],
        'created_by_id': [not_empty, six.text_type, remove_whitespace],
    }
    return schema


def uri_unique(uri, context):
    result = MintedURI.Session.query(MintedURI).\
        filter_by(uri=uri).first()
    if result:
        raise Invalid(_('That URI is already reserved (same type and name as an existing URI)'))
    return uri


def generate_uri(domain, type, name):
    namespace = join('id', type.lower())
    namespace_with_name = join(namespace, name.lower())
    # [site_url]/id/[type]/[name] is used to generate a consistent uuid5
    # The same type/name for the same site url should always provide the
    # same guid
    guid_url = urljoin(domain, quote(namespace_with_name))
    guid = str(uuid.uuid5(uuid.NAMESPACE_URL, guid_url))

    # Final uri is [site_url]/id/[type]/[guid]
    path = quote(join(namespace, guid))
    return urljoin(domain, path)


class MintedURI(DomainObject):
    @classmethod
    def create(cls, data_dict):
        '''
        Create a new MintedURI instance.

        The URI is built from the base url of the site, a supplied `type` and a generated guid
        This is stored with a supplied `name` to provide a way of dereferencing the URI to
        a known name for the entity it describes.

        The given `name` should be unique within the `type` (or namespace).
        '''
        # Validate form input data
        validated_data, errors = validate(data_dict, default_schema())
        if errors:
            raise ValidationError(errors)

        # Generate a URI from the validated data
        type = validated_data.get('type')
        name = validated_data.get('name')
        created_by_id = validated_data.get('created_by_id')
        domain = config.get('ckan.site_url', '').strip()

        uri = generate_uri(domain, type, name)

        # Validate that the URI is unique
        valid_uri, errors = validate({ 'uri': uri }, { 'uri': [uri_unique]})
        if errors:
            raise ValidationError(errors)

        model = MintedURI(
            uri=valid_uri.get('uri'),
            type=type,
            name=name,
            created_by_id=created_by_id,
        )
        model.save()

        return model

    def __repr__(self):
        return '<MintedURI uri={} name={}>'\
            .format(self.uri, self.name)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')
