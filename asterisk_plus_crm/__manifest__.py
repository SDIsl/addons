# ©️ OdooPBX by Odooist, Odoo Proprietary License v1.0, 2021
# -*- encoding: utf-8 -*-
{
    'name': 'Asterisk Plus CRM',
    'version': '1.0',
    'author': 'Odooist',
    'price': 0,
    'currency': 'EUR',
    'maintainer': 'Odooist',
    'support': 'odooist@gmail.com',
    'license': 'LGPL-3',
    'category': 'Phone',
    'summary': 'Asterisk Plus CRM integration',
    'description': "",
    'depends': ['crm', 'asterisk_plus'],
    'data': [
        'security/server.xml',
        'views/crm_lead.xml',
        'views/call.xml',
        'views/settings.xml',
        
    ],
    'demo': [],
    "qweb": ['static/src/xml/*.xml'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
