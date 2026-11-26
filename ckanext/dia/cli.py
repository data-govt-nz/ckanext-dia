# encoding: utf-8
import click
from ckanext.dia import utils, model


def get_commands():
    return [dia]


@click.group(short_help=u"Helpful commands provided by DIA plugin")
def dia():
    pass


@dia.command()
@click.option(
    '--include-deleted-datasets', is_flag=True, default=False,
    help=u'Also delete DataStore tables of resources whose dataset is '
         u'soft-deleted (state=deleted) with no edits or activity '
         u'(including its deletion) in the last --grace-days days. '
         u'Off by default.')
@click.option(
    '--grace-days', type=click.IntRange(min=0),
    default=utils.DEFAULT_DELETED_GRACE_DAYS, show_default=True,
    help=u'With --include-deleted-datasets: only datasets deleted more than '
         u'this many days ago are cleaned.')
@click.option(
    '--dry-run', is_flag=True, default=False,
    help=u'Report the number and total size of tables that would be '
         u'deleted, without deleting anything.')
def cleanup_datastore(include_deleted_datasets, grace_days, dry_run):
    """
    Cleans datastore by deleting orphaned datastore resource tables

    Orphans are tables whose resource no longer exists or is deleted. With
    --include-deleted-datasets, tables of resources inside long-deleted
    datasets are removed too (and their datastore_active flag is cleared).
    """
    return utils.cleanup_datastore(
        include_deleted_datasets=include_deleted_datasets,
        grace_days=grace_days,
        dry_run=dry_run)

@dia.command()
def init_minted_uri_db():
    """
    Create the db table for storing minted URIs
    """
    return model.db_setup()
