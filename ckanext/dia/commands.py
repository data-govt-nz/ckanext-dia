import sys
import itertools
import ckan.lib.cli
import ckan.logic as logic
import ckan.model as model


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
        resource_id_list = []
        for offset in itertools.count(start=0, step=100):
            print "Load metadata records from datastore (offset: %s)" % offset
            record_list, has_next_page = self._get_datastore_table_page(context, offset)  # noqa
            resource_id_list.extend(record_list)
            if not has_next_page:
                break

        # delete the rows of the orphaned datastore tables
        delete_count = 0
        for resource_id in resource_id_list:
            logic.get_action('datastore_delete')(
                context,
                {'resource_id': resource_id, 'force': True}
            )
            print "Table '%s' deleted (not dropped)" % resource_id
            delete_count += 1

        print "Deleted content of %s tables" % delete_count

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
                print "Resource '%s' *not* found" % record['name']
            except KeyError:
                continue

        # are there more records?
        has_next_page = (len(result['records']) > 0)

        return (resource_id_list, has_next_page)
