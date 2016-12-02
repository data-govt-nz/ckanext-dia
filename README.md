# CKANEXT-DIA

## What am I?
A simple CKAN extension to hold all overrides to CKAN required by the DIA (Department
of Internal Affairs).

## How to install?
You can use `pip` to install this plugin into your virtual environment:

```
pip install -e 'git+ssh@gitlab.wgtn.cat-it.co.nz/ckan/ckanext-dia.git#egg=ckanext-dia==0.0.1'
```

## How to activate plugins?

All plugins need to be added to `ckan.plugins` in your config file. Available
plugins are:

* `diavalidation` -- Exposes extra validators, such as `natural_num_or_missing`
* `diaschema` -- DIA-related changes to CKAN schema
