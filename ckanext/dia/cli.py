# encoding: utf-8
import click
import ckanext.dia.utils as utils

def get_commands():
    return [dia]

@click.group(short_help=u"Helpful commands provided by DIA plugin")
def dia():
    pass

@dia.command()
def cleanup_datastore():
    """
    Cleans datastore by deleting datastore resource tables
    that are no longer referenced by datasets
    """
    return utils.cleanup_datastore()
