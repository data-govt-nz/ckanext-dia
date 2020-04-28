import sys
import logging
import itertools
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
        # E.B 15/3/18 HACK: running the datastore 20 times in a row allows us to
        # get datastore table cleanup to work. Without this hack only 300 tables
        # will be cleaned up.
        start_offset = 0
        for i in xrange(20):
            print 'invoking iteration %s of the cleanup_datastore_once function' % i
            deletes, errors, total_tested = self.cleanup_datastore_once(start_offset)
            start_offset += total_tested - errors - deletes
            if deletes == 0:
                print 'no datastore tables remain to be deleted.'
                break

    def cleanup_datastore_once(self, start_offset):
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
        resource_id_list = []
        total_tested = 0
        for offset in itertools.count(start=start_offset, step=100):
            print "Load metadata records from datastore (offset: %s)" % offset
            record_list, tested = self._get_datastore_table_page(context, offset)  # noqa
            total_tested += tested
            resource_id_list.extend(record_list)
            if not tested > 0:
                break
            if len(resource_id_list) > 250:
                # Run a small chunk of the dataset to avoid locking up the
                # database for a *really* long time(read: until postgres is
                # restarted)
                break

        print('Total resources missing but referenced in datastore: {}'.format(len(resource_id_list)))

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


        # delete the rows of the orphaned datastore tables
        delete_count = 0
        delete_error_count = 0

        for resource_id in resource_id_list:
            count = datastore_record_count(context, resource_id)
            if count is not None:
                print('Deleting datastore table with {} entries for resource {} ...'.format(count, resource_id))
            else:
                print('No datastore table found for resource {}'.format(resource_id))
                delete_error_count += 1
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
            if count is None:
                print('Delete succeeded')
                delete_count += 1
            else:
                print('Delete failed! (search for datastore table succeeded)')
                delete_error_count += 1

        print "Deleted %s datastore tables" % delete_count
        print "Deletion failed for %s tables" % delete_error_count
        return (delete_count, delete_error_count, total_tested)

    def _get_datastore_table_page(self, context, offset=0):
        # query datastore to get all resources from the _table_metadata
        result = logic.get_action('datastore_search')(
            context,
            {
                'resource_id': '_table_metadata',
                'offset': offset
            }
        )

        resource_id_list = []
        for record in result['records']:
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
                resource_id_list.append(record['name'])
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

        tested = len(result['records'])
        return (resource_id_list, tested)
