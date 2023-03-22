# encoding: utf-8

from __future__ import print_function
import datetime
import logging
import sys

from ckan import model
from ckan.model import DomainObject, User
from ckan.model.meta import metadata, mapper
from ckan.plugins import toolkit
from sqlalchemy import Table, Column, types

log = logging.getLogger(__name__)
minted_uri_table = None


def db_setup():
    if minted_uri_table is None:
        define_table()

    if not model.package_table.exists():
        log.critical("Exiting: can not migrate minted uri model \
if the database does not exist yet")
        sys.exit(1)
        return

    if not minted_uri_table.exists():
        minted_uri_table.create()
        print("Created Minted URI table")
    else:
        print("Minted URI table already exists -- skipping")


def define_table():
    global minted_uri_table
    if minted_uri_table is not None:
        return
    minted_uri_table = Table(
        'minted_uri', metadata,
        Column('id', types.Integer, primary_key=True),
        Column('uri', types.UnicodeText, default=u''),
        Column('created_by_id', types.UnicodeText, default=u''),
        Column('created_at', types.DateTime))

    mapper(
        MintedURI,
        minted_uri_table
    )


class MintedURI(DomainObject):
    @classmethod
    def create(cls):
        '''TODO'''

    def __repr__(self):
        return '<MintedURI uri={} >'\
            .format(self.uri)

    def __str__(self):
        return self.__repr__().encode('ascii', 'ignore')
