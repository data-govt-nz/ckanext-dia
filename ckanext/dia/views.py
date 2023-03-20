# -*- coding: utf-8 -*-
from logging import getLogger
from flask import Blueprint, redirect
from ckan.plugins import toolkit as tk

log = getLogger(__name__)


dia = Blueprint("dia", __name__)


def redirect_to_search():
    return redirect('/dataset')


dia.add_url_rule(
    "/",
    view_func=redirect_to_search
)


uris = Blueprint("uris", __name__)

def new_uri():
    return tk.render('uris/new.html')

uris.add_url_rule('/uri/new', view_func=new_uri, methods=['GET', 'POST'])


def get_blueprints():
    return [dia, uris]
