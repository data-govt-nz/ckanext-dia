# -*- coding: utf-8 -*-
from logging import getLogger
from flask import Blueprint, redirect
from ckan.plugins import toolkit as tk
from ckan.common import _, g, request
import ckan.lib.base as base

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
    if request.method == 'POST':
        datatype = request.form.get('datatype')
        identifier = request.form.get('identifier')

        log.critical(datatype)

        return tk.render('uris/success.html')

    return tk.render('uris/new.html')
