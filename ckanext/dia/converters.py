from builtins import map
import re
from logging import getLogger

log = getLogger(__name__)


def fix_code_style_list(key, data, errors, context):
    """Grant's code style fix converter"""
    from ast import literal_eval as safe_eval

    ## As per method signature this is for editing data, not returning a value
    raw = data.get(key)
    try:
        py_list = safe_eval(raw)
    except ValueError as e:
        ## only warnings seem to make it through the CKAN logging (and appear in /var/log/apache2/ckan_default.error.log)
        log.info("Unable to clean value {} - already a clean string? {}".format(raw, e))
        return None
    except Exception as e:
        log.info(u"Unable to clean value {} - {}".format(raw, e))
        return None
    else:
        if isinstance(py_list, list):
            log.info(u"Converted code-style list '{}' into text format".format(raw))
            data[key] = u' & '.join(py_list)


def strip_invalid_tags_content(tags):
    '''Takes a list of tag dicts, converts invalid characters to spaces
    and then removes any duplicate spaces.'''

    def convert_tag(tag):
        # Replace bad characters with spaces
        tag['name'] = re.sub('[^\w|^\-|^\.]', ' ', tag['name'])
        # Remove redundant spaces
        tag['name'] = re.sub(' {2,}', ' ', tag['name'])
        return tag

    return list(map(convert_tag, tags))
