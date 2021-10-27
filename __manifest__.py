# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2020
# -*- encoding: utf-8 -*-
{
    'name': 'Asterisk Plus',
    'version': '1.0',
    'author': 'Odooist',
    'price': 100.0,
    'currency': 'EUR',
    'maintainer': 'Odooist',
    'support': 'odooist@gmail.com',
    'license': 'OPL-1',
    'category': 'Phone',
    'summary': 'Asterisk plus Odoo',
    'description': 'Asterisk plus Odoo',
    'depends': ['base', 'mail'],
    'data': [
        # Security rules
        'security/groups.xml',
        'security/server.xml',
        'security/admin.xml',
        'security/user.xml',
        'security/channel.xml',
        # Data
        'data/events.xml',
        'data/res_users.xml',
        'data/server.xml',
        # UI Views
        'views/assets.xml',
        'views/menu.xml',
        'views/server.xml',
        'views/settings.xml',
        'views/about.xml',
        'views/event.xml',
        'views/res_users.xml',
        'views/user.xml',
        'views/res_partner.xml',
        'views/channel.xml',
        'views/templates.xml',
        # Cron
        'views/ir_cron.xml',
    ],
    'demo': [],
    "qweb": ['static/src/xml/*.xml'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/logo.png'],
}
