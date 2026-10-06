from builtins import map
import datetime
import re
from logging import getLogger

import dateutil.parser

from ckan.lib import helpers as h

log = getLogger(__name__)

# Fills the parts missing from a partial date; must never depend on today's date
_PARTIAL_DATE_DEFAULT = datetime.datetime(2000, 1, 1)


def fix_code_style_list(key, data, errors, context):
    """Grant's code style fix converter"""
    from ast import literal_eval as safe_eval

    # As per method signature this is for editing data, not returning a value
    raw = data.get(key)
    try:
        py_list = safe_eval(raw)
    except ValueError as e:
        # only warnings seem to make it through the CKAN logging (and appear
        # in /var/log/apache2/ckan_default.error.log)
        log.info(
            "Unable to clean value {} - already a clean string? {}"
            .format(raw, e))
        return None
    except Exception as e:
        log.info(u"Unable to clean value {} - {}".format(raw, e))
        return None
    else:
        if isinstance(py_list, list):
            log.info(
                u"Converted code-style list '{}' into text format"
                .format(raw))
            data[key] = u' & '.join(py_list)


def strip_invalid_tags_content(tags):
    '''Takes a list of tag dicts, converts invalid characters to spaces
    and then removes any duplicate spaces.'''

    def convert_tag(tag):
        # Replace bad characters with spaces
        tag['name'] = re.sub(r'[^\w|^\-|^\.]', ' ', tag['name'])
        # Remove redundant spaces
        tag['name'] = re.sub(' {2,}', ' ', tag['name'])
        return tag

    return list(map(convert_tag, tags))


def to_ckan_date(value):
    """Normalise a harvested date string to one CKAN's `isodate` validator
    accepts, or return None if it can't be parsed.

    dateutil accepts things CKAN rejects (a trailing `Z`, any number of
    fractional digits), and a rejected resource `last_modified` fails the whole
    dataset, so convert to a naive UTC `isoformat()` string and check it with
    CKAN's own parser.

    Partial dates ("2019", "2019-05") are valid ISO 8601, but dateutil fills the
    missing parts from today's date, which would give the resource a new
    last_modified (and an xloader reload) on every harvest. Fill them from a
    fixed default instead so the result is stable.
    """
    if not value:
        return None
    try:
        parsed = dateutil.parser.parse(value, default=_PARTIAL_DATE_DEFAULT)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(
                datetime.timezone.utc).replace(tzinfo=None)
        normalised = parsed.isoformat()
        h.date_str_to_datetime(normalised)
    except (ValueError, OverflowError, TypeError):
        log.warning('Ignoring unparseable date %r', value)
        return None
    return normalised
