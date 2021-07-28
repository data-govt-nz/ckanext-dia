# -*- coding: utf-8 -*-
from logging import getLogger
from flask import Blueprint, redirect

log = getLogger(__name__)


dia = Blueprint("dia", __name__)

def redirect_to_search():
    return redirect('/dataset')

dia.add_url_rule(
    "/",
    view_func=redirect_to_search
)

def get_blueprints():
    return [dia]
