from logging import getLogger
log = getLogger(__name__)

iso_8601_frequency = {
    "R/P1Y": "Annual",
    "R/P2Y": "Biennial",
    "R/P2M": "Bimonthly",
    "R/P0.5M": "Bimonthly",
    "R/P0.5W": "Biweekly",
    "R/P2W": "Biweekly",
    "R/PT1S": "Continuously updated",
    "R/P1D": "Daily",
    "R/P10Y": "Decennial",
    "R/PT1H": "Hourly",
    "R/P1M": "Monthly",
    "R/P4Y": "Quadrennial",
    "R/P3M": "Quarterly",
    "R/P6M": "Semiannual",
    "R/P0.5M": "Semimonthly",
    "R/P3.5D": "Semiweekly",
    "R/P0.33M": "Three times a month",
    "R/P0.33W": "Three times a week",
    "R/P4M": "Three times a year",
    "R/P3Y": "Triennial",
    "R/P1W": "Weekly"
}

non_iso_8601_to_iso_8601_frequency = {
    "6-Monthly": "Semiannual",
    "Annually": "Annual",
    "As Required": "Irregular",
    "Other-Unknown": "Irregular",
    "Realtime": "Continuously updated",
    "Static": "Irregular",
    "Unknown": "Irregular",
    "Yearly": "Annual",
}

csw_non_iso_8601_to_iso_8601_frequency = {
    "annually": "Annual",
    "asneeded": "Irregular",
    "biannually": "Biennial",
    "continual": "Continuously updated",
    "daily": "Daily",
    "irregular": "Irregular",
    "monthly": "Monthly",
    "notplanned": "Irregular",
    "quarterly": "Quarterly",
    "unknown": "Irregular",
    "weekly": "Weekly",
}


def clean_frequency(frequency):
    """
    Frequency (accrualPeriodicity) must match the ISO 8601 term.

    In the database the frequency stored should the the ISO-8601 English
    equvivalent. The following cleaning is done:
    - If the frequency is already the English equivalent it is returned.
    - ISO-8601 terms are mapped to the English equivalent.
    - Some other obvious mappings are also mapped to the ISO-8601 terms.
    - All other things are set to Irregular and and logged.
    """
    log.debug("_clean_frequency: {0}".format(frequency))
    if frequency in iso_8601_frequency.values():
        return frequency
    if frequency in iso_8601_frequency:
        return iso_8601_frequency[frequency]
    if frequency in non_iso_8601_to_iso_8601_frequency:
        log.info("Harvested frequency of {0} mapped to {1}:".format(frequency, non_iso_8601_to_iso_8601_frequency[frequency]))
        return non_iso_8601_to_iso_8601_frequency[frequency]
    if frequency.lower() in csw_non_iso_8601_to_iso_8601_frequency:
        return csw_non_iso_8601_to_iso_8601_frequency[frequency.lower()]

    log.warning("frequency_of_update found in dcat harvesting is an unknown value: {0}".format(frequency))
    return 'Irregular'
