from setuptools import setup, find_packages

version = '1.3.1'

setup(
    name='ckanext-dia',
    version=version,
    description='DIA-related modifications to CKAN',
    long_description='',
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[],
    keywords='',
    author='Data.govt.nz',
    author_email='info@data.govt.nz',
    url='https://www.data.govt.nz',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext', 'ckanext.dia'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "pycountry",
        "pyproj",
        "future"
    ],
    entry_points="""
    [ckan.plugins]
    diavalidation=ckanext.dia.plugin:DIAValidationPlugin
    diaschema=ckanext.dia.plugin:DIASchemaPlugin
    diaactions=ckanext.dia.plugin:DIAActionsPlugin
    diaharvester=ckanext.dia.harvester.csw:DIASpatialHarvester
    diadcatjsonharvester=ckanext.dia.harvester.dcat:DIADCATJSONHarvester
    dianohomepage=ckanext.dia.plugin:DIANoHomepagePlugin
    diacommands=ckanext.dia.plugin:DIACommandsPlugin

    [paste.paster_command]
    admin=ckanext.dia.commands:AdminCommand
    """,
)
