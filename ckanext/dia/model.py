# encoding: utf-8

from __future__ import print_function
import datetime
import logging
import sys
import six
from sqlalchemy import Table, Column, types, ForeignKey, desc, func
from sqlalchemy.sql.expression import or_
from urllib.parse import urljoin, quote
from os import path
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
        Column('created_at', types.DateTime, default=datetime.datetime.utcnow),
        Column('updated_by_id', types.UnicodeText, ForeignKey('user.id')),
        Column('updated_at', types.DateTime),
        Column('superseded_by', types.Integer))
    mapper(
        MintedURI,
        minted_uri_table
    )


def name_and_type_unique(name, context):
    type = context.get('type')
    result = MintedURI.Session.query(MintedURI)\
        .filter(func.lower(MintedURI.name) == name.lower())\
        .filter(func.lower(MintedURI.type) == type.lower())\
        .filter(MintedURI.superseded_by == None)\
        .first()
    if result:
        raise Invalid(_('That URI is already reserved (same type and name as an existing URI)'))
    return name


def uri_unique(uri, context):
    result = MintedURI.Session.query(MintedURI).\
        filter_by(uri=uri).first()
    if result:
        raise Invalid(_('There is an existing identical URI, please submit the form again to generate a new one'))
    return uri


def no_type_change(type, context):
    old_type = context.get('type')
    if type != old_type:
        raise Invalid(_('The type cannot be changed once the URI has been minted'))
    return type


def default_schema():
    schema = {
        'type': [not_empty, six.text_type, remove_whitespace],
        'name': [not_empty, six.text_type, remove_whitespace, name_and_type_unique],
        'created_by_id': [not_empty, six.text_type, remove_whitespace],
    }
    return schema


def update_schema(regenerating):
    schema = {
        'type': [no_type_change],
        'name': [not_empty, six.text_type, remove_whitespace],
        'updated_by_id': [not_empty, six.text_type, remove_whitespace],
    }
    if not regenerating:
        schema['name'].append(name_and_type_unique)
    return schema


def generate_uri(type):
    domain = config.get('ckan.site_url', '').strip()
    namespace = path.join('id', type.lower())
    guid = str(uuid.uuid1())
    path_section = quote(path.join(namespace, guid))

    # Final uri is [site_url]/id/[type]/[guid]
    return urljoin(domain, path_section)


def set_updated_props(model, updated_by_id):
    model.updated_by_id = updated_by_id
    model.updated_at = datetime.datetime.utcnow()
    return model


class MintedURI(DomainObject):
    @classmethod
    def get(cls, uri_id):
        '''
        Get a URI instance by it's ID
        '''
        return MintedURI.Session.query(MintedURI).get(uri_id)


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
        validated_data, errors = validate(data_dict, default_schema(), data_dict)
        if errors:
            raise ValidationError(errors)

        # Generate a URI from the validated data
        type = validated_data.get('type')
        name = validated_data.get('name')
        created_by_id = validated_data.get('created_by_id')
        uri = generate_uri(type)

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

    @classmethod
    def update(cls, uri_id, data_dict):
        '''
        Update an existing MintedURI instance.

        The URI can be regenerated if the entity has changed it's remit altogether,
        or the name may be changed if the entity has not changed it's remit, but only it's
        known name. A name change should not generate a new URI.

        The given `name` should be unique within the `type` (or namespace).
        '''
        model = MintedURI.get(uri_id)
        context = { 'name': model.name, 'type': model.type }
        regenerating = data_dict.get('regenerate', False)

        # Validate form input data
        validated_data, errors = validate(data_dict, update_schema(regenerating), context)
        if errors:
            raise ValidationError(errors)

        type = validated_data.get('type')
        name = validated_data.get('name')
        updated_by_id = validated_data.get('updated_by_id')

        if regenerating:
            # Validate that the new URI is unique
            uri = generate_uri(type)
            valid_uri, errors = validate({ 'uri': uri }, { 'uri': [uri_unique]})
            if errors:
                raise ValidationError(errors)

            # Create a new minted URI with the same type and name
            new_model = MintedURI(
                uri=valid_uri.get('uri'),
                type=type,
                name=name,
                created_by_id=updated_by_id,
            )
            new_model.save()

            # Mark original URI as superseded by the new one
            # so that we can trace the links between them if needed
            model.superseded_by = new_model.id
            model = set_updated_props(model, updated_by_id)
            model.save()

            return new_model

        # Only updating the name on the URI
        model.name = name
        model = set_updated_props(model, updated_by_id)
        model.save()

        return model

    @classmethod
    def get_list(cls, data_dict):
        q = data_dict.get('q', '')

        query = MintedURI.Session.query(MintedURI)\
            .filter(MintedURI.superseded_by == None)\
            .order_by(desc(MintedURI.created_at))

        if q:
            query = MintedURI.search(q, query)

        return query

    @classmethod
    def search(cls, querystr, sqlalchemy_query):
        '''Search name and type'''
        query = sqlalchemy_query
        qstr = '%' + querystr + '%'
        filters = [
            cls.name.ilike(qstr),
            cls.type.ilike(qstr),
        ]
        query = query.filter(or_(*filters))
        return query

    def __repr__(self):
        return '<MintedURI uri={} name={}>'\
            .format(self.uri, self.name)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')
