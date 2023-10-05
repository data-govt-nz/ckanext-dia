# CKANEXT-DIA

## CKAN < 2.9 support
As of `1.3.0` this extention has been made to work with CKAN 2.9. While attempts have been made to maintain compatibility with prior version of CKAN, there may be issues. If any issues are discovered we are happy to accept PRs. Alternatively for compatibility <2.9 the `1.2.0` tag can be used.

## What am I?

A simple CKAN extension to hold all overrides to CKAN required by the DIA (Department
of Internal Affairs).

## How to install?

It is expected that you will have these other CKAN extensions installed:

- ckanext-spatial
- ckanext-dcat
- ckanext-harvester

You can use `pip` to install this plugin into your virtual environment:

```
pip install -e 'https://github.com/data-govt-nz/ckanext-dia.git#egg=ckanext-dia==1.0.0'
```

You can also install the specific dependencies using the appropriate requirements.txt file for your version of Python.

## Manual Testing for Harvesting Modifications

When working on the dcat.json or CSW harvesting extensions you often need to load testing data, you can use the following paster command to re-harvest an existing dataset:

```shell
docker-compose run --service-ports ckan-fetch ckan-paster --plugin=ckanext-harvest harvester import -p 'reefton-goldfield-sheet-12-part-of-waitahu-survey-district-and-pohaturoa-survey-district-field-1'
```

where `reefton-goldfield...` is the dataset id in the url, this may also look like a guid, both will work.

## How to activate plugins?

All plugins need to be added to `ckan.plugins` in your config file. Available
plugins are:

- `diavalidation` -- Exposes extra validators, such as `natural_num_or_missing`
- `diaschema` -- DIA-related changes to CKAN schema
- `diaharvester` -- Overrides for the CSW harvester, needs to be enabled before `csw_harvester`
- `diadcatjsonharvester` -- Overrides for the DCAT JSON harvester, needs to be enabled instead of `dcat_json_harvester`
- `dianohomepage` -- Redirect the CKAN homepage to `/dataset`
- `diacommands` -- Provides cli commands (only needed on ckan >= 2.9)
- `diauriminting` -- Provides a new data model, listing view and creation form to mint URIs for entities in linked datasets. Only supported in CKAN 2.9+ (No pylons/paster support)

## Commands

### Cleanup datastore
This extension currently provides a cli command to clean up the datastore database.
Resources are not deleted when re-harvesting. This command deletes the old resources that
are no longer referenced.

```bash
# ckan >= 2.9
ckan -c /PATH_TO_YOUR_INI_FILE/FILENAME.ini dia cleanup-datastore

# ckan < 2.9
paster --plugin=ckanext-dia admin cleanup_datastore -c /PATH_TO_YOUR_INI_FILE/FILENAME.ini
```

Note: That if your default_datastore is very large this may time out and need
to be restarted. Also although it deletes the resource's tables from the
datastore_default it does not delete entries from archival, resource,
resource_revision and resource_view.
It also failed on the first run to delete some resources but they were deleted on subsequent runs.

Thanks @opendata-swiss who wrote the command at https://github.com/opendata-swiss/ckanext-switzerland

### Initialise database for minting URIs
A one off migration command to create the database table needed to store the minted URIs. Only available in CKAN 2.9+.
```bash
ckan -c /PATH_TO_YOUR_INI_FILE/FILENAME.ini dia init-minted-uri-db
```
