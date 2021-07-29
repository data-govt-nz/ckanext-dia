from __future__ import print_function
import sys
from ckantoolkit import CkanCommand
import ckanext.dia.utils as utils


class AdminCommand(CkanCommand):
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
            'cleanup_datastore': utils.cleanup_datastore,
            'help': self.help,
        }

        try:
            cmd = self.args[0]
            options[cmd](*self.args[1:])
        except KeyError:
            self.help()
            sys.exit(1)

    def help(self):
        print(self.__doc__)


