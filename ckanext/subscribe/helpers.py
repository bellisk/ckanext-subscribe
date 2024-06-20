import ckan.plugins.toolkit as tk


def get_recaptcha_publickey():
    """Get reCaptcha public key.
    """
    return tk.config.get('ckanext.subscribe.recaptcha.publickey')

def apply_recaptcha():
    """Apply recaptcha"""
    apply_recaptcha = tk.asbool(
        tk.config.get('ckanext.subscribe.apply_recaptcha', True))
    return apply_recaptcha
