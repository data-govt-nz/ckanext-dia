from __future__ import print_function
import sys
import logging
import itertools
import time
import datetime
import ckan.logic as logic
import ckan.model as model
from ckan.common import config
from ckan.model import Session, User, ApiToken
import sqlalchemy as sa

logger = logging.getLogger(__name__)


DEFAULT_DELETED_GRACE_DAYS = 30


def cleanup_datastore(include_deleted_datasets=False,
                      grace_days=DEFAULT_DELETED_GRACE_DAYS,
                      dry_run=False):
    """
    Delete DataStore tables that no longer have a live resource.

    By default only tables whose resource cannot be found (resource purged,
    or resource itself state='deleted') are removed.

    include_deleted_datasets: also remove tables belonging to resources whose
        dataset has state='deleted' and was last modified (i.e. deleted) more
        than ``grace_days`` days ago. A sysadmin can still resource_show these
        resources, so the NotFound check never catches them.
    dry_run: only report what would be deleted (counts and sizes).
    """
    user = logic.get_action('get_site_user')({'ignore_auth': True}, {})
    context = {
        'model': model,
        'session': model.Session,
        'user': user['name']
    }
    try:
        logic.check_access('datastore_delete', context)
        logic.check_access('resource_show', context)
    except logic.NotAuthorized:
        print("User is not authorized to perform this action.")
        sys.exit(1)

    # query datastore to get all resources from the _table_metadata
    print("Loading metadata records from datastore")
    all_datastore_tables = _get_all_datastore_tables(context)

    if dry_run:
        print('DRY RUN: nothing will be deleted')
    if include_deleted_datasets:
        print('Including tables for datasets deleted more than {} days ago'
              .format(grace_days))

    chunk_size = 100
    total_deleted = 0
    failed_deletes = []
    would_delete = 0
    would_delete_bytes = 0
    dataset_would_delete = 0
    skipped_rw = 0
    for offset in itertools.count(start=0, step=chunk_size):
        end_chunk_index = offset + chunk_size
        datastore_tables_chunk = all_datastore_tables[offset:end_chunk_index]
        deleted_dataset_list = []
        if include_deleted_datasets:
            deleted_dataset_list, rw_skipped = \
                _find_tables_of_deleted_datasets(
                    datastore_tables_chunk, grace_days)
            skipped_rw += rw_skipped
            already = set(deleted_dataset_list)
            # no need to resource_show tables we already know are removable
            datastore_tables_chunk = [
                r for r in datastore_tables_chunk
                if r.get('name') not in already]
        orphan_list = _find_orphaned_datastore_tables(
            context, datastore_tables_chunk)
        dataset_would_delete += len(deleted_dataset_list)
        orphan_list = orphan_list + deleted_dataset_list
        if dry_run:
            would_delete += len(orphan_list)
            would_delete_bytes += _table_sizes(orphan_list)
        elif len(orphan_list) > 0:
            # Run a small chunk of the dataset to avoid locking up the
            # database for a *really* long time(read: until postgres is
            # restarted)
            delete_count, error_list = _delete_orphans(context, orphan_list)
            total_deleted += delete_count
            failed_deletes.extend(error_list)
            print('Deleted in this chunk: {}'.format(delete_count))
            print('Errored in this chunk: {}'.format(len(error_list)))

        if end_chunk_index >= len(all_datastore_tables):
            break

        print('{} tables checked, {} more to go...'.format(
            end_chunk_index, len(all_datastore_tables) - end_chunk_index))
        time.sleep(1)

    if include_deleted_datasets:
        print('Skipped {} tables of deleted datasets that were created '
              'through the DataStore API (url_type=datastore) and cannot '
              'be reloaded'.format(skipped_rw))

    if dry_run:
        print('DRY RUN complete. Tables that would be deleted: {} '
              '(of which {} belong to deleted datasets), '
              'total size {}'.format(
                  would_delete, dataset_would_delete,
                  _human_size(would_delete_bytes)))
        return

    updated_table_count = len(_get_all_datastore_tables(context))

    print('Cleanup complete!')
    print('Total datastore tables before: {} and after: {}'.format(
        len(all_datastore_tables), updated_table_count))
    print('Total orphaned datastore tables deleted: {}'.format(total_deleted))
    print('Total errors when attempting deletion: {}'
          .format(len(failed_deletes)))
    if len(failed_deletes) > 0 and len(failed_deletes) < 10:
        # don't print if too many
        print('Datastore table names that failed to delete: {}'
              .format(failed_deletes))


def _get_all_datastore_tables(context):
    result_set = logic.get_action('datastore_search')(
        context,
        {
            'resource_id': '_table_metadata',
            'limit': 50000,  # arbitrarily high, but default limit is 100
        }
    )

    return result_set.get('records', [])


def _delete_orphans(context, resource_id_list):
    print('Batch deleting {} ophaned datastore records'
          .format(len(resource_id_list)))

    def datastore_record_count(context, resource_id):
        """
        Wraps the search so that it returns None if NotFound,
        otherwise the total
        """
        try:
            search = logic.get_action('datastore_search')(
                context,
                {'resource_id': resource_id}
            )
            count = search['total']
        except logic.NotFound:
            count = None

        return count

    # delete orphaned datastore tables
    delete_count = 0
    delete_errors = []

    for resource_id in resource_id_list:
        count = datastore_record_count(context, resource_id)
        if count is None:
            print('No datastore table found for resource {}'
                  .format(resource_id))
            delete_errors.append(resource_id)
            continue

        try:
            logic.get_action('datastore_delete')(
                context,
                {'resource_id': resource_id, 'force': True}
            )
        except AttributeError as e:
            # datastore_delete references resource.extras
            # when there is no resource
            if str(e) != "'NoneType' object has no attribute 'extras'":
                raise(e)

        count = datastore_record_count(context, resource_id)
        if count is not None:
            print('Datastore table {} failed to delete'.format(resource_id))
            delete_errors.append(resource_id)
        else:
            delete_count += 1

    return (delete_count, delete_errors)


def _find_orphaned_datastore_tables(context, datastore_tables_chunk):
    orphan_list = []
    for record in datastore_tables_chunk:
        try:
            # ignore 'alias' records
            if record['alias_of']:
                continue

            logic.get_action('resource_show')(
                context,
                {'id': record['name']}
            )
            print("Resource '%s' found" % record['name'])
        except logic.NotFound:
            orphan_list.append(record['name'])
            context.pop('__auth_audit', None)
            print("Resource '%s' *not* found" % record['name'])
        except KeyError:
            continue
        except Exception as e:
            # Added as something did not check the authorization for
            # doing a resource_show.
            print("Unexpected error looking up resource: '%s'" % (
                record['name']))
            logger.exception("Unable to lookup resource: '%s'",
                             record['name'], exc_info=e)

    return orphan_list


def _find_tables_of_deleted_datasets(datastore_tables_chunk, grace_days):
    """
    Return (names, skipped_count): the DataStore table names in the chunk
    whose resource belongs to a dataset with state='deleted' that was last
    modified more than ``grace_days`` days ago.

    This is a single query against the CKAN DB per chunk rather than a
    package_show per table. package_delete does not bump
    package.metadata_modified, so the deletion time is taken from the activity
    stream: the dataset must have no activity at all (including its 'deleted
    package' activity) within the grace period, as well as an older
    metadata_modified.

    Resources with url_type='datastore' hold data that was only ever loaded
    through the DataStore API, so the table cannot be rebuilt by xloader if
    the dataset is restored. They are skipped and counted.

    Aliases are never returned (they are views on the real table and go when
    the table is dropped).
    """
    names = [r['name'] for r in datastore_tables_chunk
             if r.get('name') and not r.get('alias_of')]
    if not names:
        return [], 0
    cutoff = (datetime.datetime.utcnow()
              - datetime.timedelta(days=grace_days))
    rows = Session.query(
        model.Resource.id, model.Resource.url_type
    ).join(
        model.Package, model.Package.id == model.Resource.package_id
    ).filter(
        model.Resource.id.in_(names),
        model.Package.state == 'deleted',
        model.Package.metadata_modified < cutoff,
        ~sa.exists(
            sa.select(sa.literal(1))
            .select_from(sa.table('activity', sa.column('object_id'),
                                  sa.column('timestamp')))
            .where(sa.and_(
                sa.column('object_id') == model.Package.id,
                sa.column('timestamp') >= cutoff))
        ),
    ).all()
    found = []
    skipped = 0
    for resource_id, url_type in rows:
        if url_type == 'datastore':
            skipped += 1
            continue
        found.append(resource_id)
    return found, skipped


def _human_size(num_bytes):
    for unit in ('bytes', 'kB', 'MB', 'GB'):
        if num_bytes < 1024 or unit == 'GB':
            return ('{:.0f} {}' if unit == 'bytes' else '{:.2f} {}').format(
                num_bytes, unit)
        num_bytes /= 1024.0


def _table_sizes(table_names):
    """Total on-disk size in bytes of the given DataStore tables (best
    effort: returns 0 if the size cannot be read)."""
    if not table_names:
        return 0
    try:
        from ckanext.datastore.backend import DatastoreBackend
        engine = DatastoreBackend.get_active_backend()._get_read_engine()
        with engine.connect() as conn:
            result = conn.execute(
                sa.text('SELECT COALESCE(SUM(pg_total_relation_size('
                        'quote_ident(n))), 0) FROM unnest(:names) AS n'),
                {'names': list(table_names)})
            return int(result.scalar() or 0)
    except Exception:
        logger.exception('Unable to read datastore table sizes')
        return 0
