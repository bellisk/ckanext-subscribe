import ckan.plugins.toolkit as tk
from datetime import timedelta


def get_recaptcha_publickey():
    """Get reCaptcha public key."""
    return tk.config.get("ckanext.subscribe.recaptcha.publickey")


def apply_recaptcha():
    """Apply recaptcha"""
    apply_recaptcha = tk.asbool(
        tk.config.get("ckanext.subscribe.apply_recaptcha", True)
    )
    return apply_recaptcha


def string_to_timedelta(s):
    """
    Convert string like '2 days' or '5 minutes' to timedelta.
    """
    parts = s.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Invalid timedelta string: {s}")
    number, unit = parts
    return timedelta(**{unit: int(number)})