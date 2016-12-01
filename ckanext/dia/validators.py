def natural_num_or_missing(value, context):
     """Allows empty strings to pass natural_number validation."""
     return value if value == '' else natural_number_validator(value, context)
