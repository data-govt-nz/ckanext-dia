import logging


def fix_code_style_list(key, data, errors, context):
    """Grant's code style fix converter"""
    from ast import literal_eval as safe_eval

    ## As per method signature this is for editing data, not returning a value
    raw = data.get(key)
    try:
        py_list = safe_eval(raw)
    except ValueError as e:
        ## only warnings seem to make it through the CKAN logging (and appear in /var/log/apache2/ckan_default.error.log)
        logging.warning("{} - Unable to clean value {} - already a clean string? {}".format(__name__, raw, e))
        return None
    except Exception as e:
        logging.warning(u"{} - Unable to clean value {} - {}".format(__name__, raw, e))
        return None
    else:
        if isinstance(py_list, list):
            logging.warning(u"{} - Converted code-style list '{}' into text format".format(__name__, raw))
            data[key] = u' & '.join(py_list)
