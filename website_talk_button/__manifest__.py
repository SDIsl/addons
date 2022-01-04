{
    'name': 'Website Talk Button',
    'description': """Let's talk. One click call using WebRTC and SIP""",
    'currency': 'EUR',
    'price': '0',
    'version': '1.0',
    'category': 'Website/Website',
    'author': 'Odooist',
    'license': 'OPL-1',
    'installable': True,
    'application': False,
    'auto_install': False,
    'depends': ['website'],
    'data': [
        'security/model_access.xml',
        'views/templates.xml',
        'views/snippets.xml',
        'views/res_config_settings_views.xml'
    ],
    'demo': [],
    'js': ['static/src/js/*.js'],
    'qweb': [
        'static/src/xml/*.xml',
    ],
}
