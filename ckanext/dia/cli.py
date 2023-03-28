# encoding: utf-8
import click
from ckanext.dia import utils, model


def get_commands():
    return [dia]


@click.group(short_help=u"Helpful commands provided by DIA plugin")
def dia():
    pass


@dia.command()
def cleanup_datastore():
    """
    Cleans datastore by deleting orphaned datastore resource tables
    """
    return utils.cleanup_datastore()

@dia.command()
def init_minted_uri_db():
    """
    Create the db table for storing minted URIs
    """
    return model.db_setup()
