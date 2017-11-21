# CKANEXT-DIA

## What am I?
A simple CKAN extension to hold all overrides to CKAN required by the DIA (Department
of Internal Affairs).

## How to install?
You can use `pip` to install this plugin into your virtual environment:

```
pip install -e 'https://github.com/data-govt-nz/ckanext-dia.git#egg=ckanext-dia==0.0.1'
```

## How to activate plugins?

All plugins need to be added to `ckan.plugins` in your config file. Available
plugins are:

* `diavalidation` -- Exposes extra validators, such as `natural_num_or_missing`
* `diaschema` -- DIA-related changes to CKAN schema
* `diaactions` -- Disables the use of caching for showing packages
* `diaharvester` -- Overrides for the CSW harvester, needs to be enabled before `csw_harvester`
* `diadcatjsonharvester` -- Overrides for the DCAT JSON harvester, needs to be enabled instead of `dcat_json_harvester`
* `dianohomepage` -- Redirect the CKAN homepage to `/dataset`

## Command

This extension currently provides a paster command to clean up the datastore database.
Resources are not deleted when re-harvesting. This command deletes the old resources that
are no longer referenced.

```bash
paster --plugin=ckanext-dia admin cleanup_datastore -c /PATH_TO_YOUR_INI_FILE/dev.ini
```

Thanks @opendata-swiss who wrote the command at https://github.com/opendata-swiss/ckanext-switzerland
