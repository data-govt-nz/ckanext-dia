import six
import datetime

from ckan.common import _
from ckan.lib import helpers as helpers
from ckan.lib.navl.dictization_functions import Invalid
import ckan.plugins as p

natural_number_validator = p.toolkit.get_validator('natural_number_validator')


def natural_num_or_missing(value, context):
    """Allows empty strings to pass natural_number validation."""
    return value if value == '' else natural_number_validator(value, context)


def isodate(value, context):
    if isinstance(value, datetime.datetime):
        return value
    if value == '':
        return None
    try:
        return helpers.date_str_to_datetime(value)
    except (TypeError, ValueError):
        raise Invalid(_('Date format incorrect - isodate') +
                      ": {}".format(value))


def extra_key_not_in_root_schema(key, data, errors, context):
    """Disabled for historic reasons"""
    return


def force_lower(value, context=None):
    """Converts strings to lowercase, does nothing for other objects."""
    return value.lower() if isinstance(value, six.string_types) else value


def ensure_str(value):
    return six.text_type(value)
