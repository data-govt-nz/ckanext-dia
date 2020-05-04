import sys
import logging
import itertools
import time
import ckan.lib.cli
import ckan.logic as logic
import ckan.model as model

logger = logging.getLogger('ckan.logic')


class AdminCommand(ckan.lib.cli.CkanCommand):
    '''Command for datastore cleanup
    Usage: paster --plugin=ckanext-dia admin <command> -c <path to config file>

        command:
        help  - prints this help
        cleanup_datastore -    Cleans datastore by deleting datastore resource tables
                               that are no longer referenced by datasets

    This command originally came from ckanext-switzerland
                https://github.com/opendata-swiss/ckanext-switzerland/
    '''
    summary = __doc__.split('\n')[0]
    usage = __doc__

    def command(self):
        # load pylons config
        self._load_config()
        options = {
            'cleanup_datastore': self.cleanup_datastore,
            'help': self.help,
        }

        try:
            cmd = self.args[0]
            options[cmd](*self.args[1:])
        except KeyError:
            self.help()
            sys.exit(1)

    def help(self):
        print self.__doc__

    def cleanup_datastore(self):
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
            print "User is not authorized to perform this action."
            sys.exit(1)

        # query datastore to get all resources from the _table_metadata
        print("Loading metadata records from datastore")
        all_datastore_tables = self._get_all_datastore_tables(context)

        chunk_size = 100
        total_deleted = 0
        failed_deletes = []
        for offset in itertools.count(start=0, step=chunk_size):
            end_chunk_index = offset + chunk_size
            datastore_tables_chunk = all_datastore_tables[offset:end_chunk_index]
            orphan_list = self._find_orphaned_datastore_tables(context, datastore_tables_chunk)
            if len(orphan_list) > 0:
                # Run a small chunk of the dataset to avoid locking up the
                # database for a *really* long time(read: until postgres is
                # restarted)
                delete_count, error_list = self._delete_orphans(context, orphan_list)
                total_deleted += delete_count
                failed_deletes.extend(error_list)
                print('Deleted in this chunk: {}'.format(delete_count))
                print('Errored in this chunk: {}'.format(len(error_list)))

            if end_chunk_index >= len(all_datastore_tables):
                break

            print('{} tables checked, {} more to go...'.format(end_chunk_index, len(all_datastore_tables) - end_chunk_index))
            time.sleep(1)

        updated_table_count = len(self._get_all_datastore_tables(context))

        print('Cleanup complete!')
        print('Total datastore tables before: {} and after: {}'.format(len(all_datastore_tables), updated_table_count))
        print('Total orphaned datastore tables deleted: {}'.format(total_deleted))
        print('Total errors when attempting deletion: {}'.format(len(failed_deletes)))
        if len(failed_deletes) > 0 and len(failed_deletes) < 10: # don't print if too many
            print('Datastore table names that failed to delete: {}'.format(failed_deletes))

    def _get_all_datastore_tables(self, context):
        result_set = logic.get_action('datastore_search')(
            context,
            {
                'resource_id': '_table_metadata',
                'limit': 50000, # arbitrarily high, but default limit is 100
            }
        )

        return result_set.get('records', [])


    def _delete_orphans(self, context, resource_id_list):
        print('Batch deleting {} ophaned datastore records'.format(len(resource_id_list)))

        def datastore_record_count(context, resource_id):
            """
            Wraps the search so that it returns None if NotFound, otherwise the total
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
                print('No datastore table found for resource {}'.format(resource_id))
                delete_errors.append(resource_id)
                continue

            try:
                logic.get_action('datastore_delete')(
                    context,
                    {'resource_id': resource_id, 'force': True}
                )
            except AttributeError as e:
                # datastore_delete references resource.extras when there is no resource
                if e.message != "'NoneType' object has no attribute 'extras'":
                    raise(e)

            count = datastore_record_count(context, resource_id)
            if count is not None:
                print('Datastore table {} failed to delete'.format(resource_id))
                delete_errors.append(resource_id)
            else:
                delete_count += 1

        return (delete_count, delete_errors)

    def _find_orphaned_datastore_tables(self, context, datastore_tables_chunk):
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
                print "Resource '%s' found" % record['name']
            except logic.NotFound:
                orphan_list.append(record['name'])
                context.pop('__auth_audit', None)
                print "Resource '%s' *not* found" % record['name']
            except KeyError:
                continue
            except Exception as e:
                # Added as something did not check the authorization for
                # doing a resource_show.
                print "Unexpected error looking up resource: '%s'" % (
                      record['name'])
                logger.exception("Unable to lookup resource: '%s'",
                                 record['name'], exc_info=e)

        return orphan_list
