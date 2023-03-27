# -*- coding: utf-8 -*-
from logging import getLogger
from flask import Blueprint, redirect

from ckan.logic import ValidationError
from ckan.plugins import toolkit as tk
from ckan.common import _, g, request
from ckan.lib import base
from ckanext.dia.model import MintedURI

log = getLogger(__name__)


no_home_page = Blueprint("no_home_page", __name__)

@no_home_page.route('/', methods=['GET', 'POST'])
def redirect_to_search():
    return redirect('/dataset')


uri_minter = Blueprint("uri_minter", __name__, template_folder='templates')

@uri_minter.before_request
def before_request():
    if not g.userobj:
        base.abort(403, _(u'Not authorized to see this page'))

@uri_minter.route('/uri/new', methods=['GET', 'POST'])
def new_uri():
    vars = {'data': None, 'errors': None, 'error_summary': None}
    if request.method == 'POST':
        datatype = request.form.get('type')
        name = request.form.get('name')
        vars['data'] = request.form

        try:
            new_instance = MintedURI.create({
                'type': datatype,
                'name': name,
                'created_by_id': g.userobj.id,
            })

            vars['data'] = {
                'uri': new_instance.uri,
                'name': new_instance.name,
            }
            return tk.render('uris/success.html', extra_vars=vars)
        except ValidationError as e:
            vars['errors'] = e.error_dict
            vars['error_summary'] = e.error_summary
        except Exception as e:
            log.error('Unknown error: %s', e, stack_info=True)
            vars['error_summary'] = { 'Error': _('An unknown error occurred') }

    return tk.render('uris/new.html', extra_vars=vars)
