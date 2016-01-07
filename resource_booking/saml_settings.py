# -*- coding: utf-8 -*-
import saml2
import saml2.saml
import os

SAML_BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'saml'
)

# URL to redirect to for starting login login-process
LOGIN_URL = '/saml2/login/'
# Should djangosaml2 logins be allowed to last past browser close?
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SAML_BASE_URL = 'https://kubooking.magenta-aps.dk'
SAML_SP_NAME = 'kubooking.magenta-aps.dk'

SAML_CERT_FILE = '/etc/apache2/ssl/magenta-aps.dk.crt'
SAML_CERT_KEY_FILE = '/etc/apache2/ssl/magenta-aps.dk.key'

SAML_REMOTE = 'https://t-login.ku.dk'
SAML_REMOTE_METADATA_URL = "".join([
    SAML_REMOTE,
    '/FederationMetadata/2007-06/FederationMetadata.xml'
])
SAML_REMOTE_SSO_URL = "".join([SAML_REMOTE, '/adfs/ls/'])
SAML_REMOTE_LOGOUT_URL = "".join([SAML_REMOTE, '/adfs/ls/?wa=wsignout1.0'])

local_saml_settings_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'local_saml_settings.py'
)
if os.path.exists(local_saml_settings_file):
    from local_saml_settings import *  # noqa

SAML_CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': SAML_BASE_URL + '/saml2/metadata/',

    # directory with attribute mapping
    'attribute_map_dir': os.path.join(SAML_BASE_DIR, 'attribute-maps'),

    # this block states what services we provide
    'service': {
        # we are just a lonely SP
        'sp': {
            'name': SAML_SP_NAME,
            'name_id_format': saml2.saml.NAMEID_FORMAT_PERSISTENT,
            'endpoints': {
                # url and binding to the assetion consumer service view
                # do not change the binding or service name
                'assertion_consumer_service': [
                    (SAML_BASE_URL + '/saml2/acs/',
                     saml2.BINDING_HTTP_POST),
                ],
                # url and binding to the single logout service view
                # do not change the binding or service name
                'single_logout_service': [
                    (SAML_BASE_URL + '/saml2/ls/',
                     saml2.BINDING_HTTP_REDIRECT),
                    (SAML_BASE_URL + '/saml2/ls/post',
                     saml2.BINDING_HTTP_POST),
                ],
            },

            # attributes that this project need to identify a user
            'required_attributes': [
                'upn'
            ],

            # attributes that may be useful to have but not required
            'optional_attributes': [
                'emailAddress',
                'givenName',
                'surname',
                'group'
            ],

            # in this section the list of IdPs we talk to are defined
            'idp': {
                # we do not need a WAYF service since there is
                # only an IdP defined here. This IdP should be
                # present in our metadata

                # the keys of this dictionary are entity ids
                'https://localhost/simplesaml/saml2/idp/metadata.php': {
                    'single_sign_on_service': {
                        saml2.BINDING_HTTP_REDIRECT: "".join([
                            "https://localhost/simplesaml/",
                            "saml2/idp/SSOService.php",
                        ])
                    },
                    'single_logout_service': {
                        saml2.BINDING_HTTP_REDIRECT: "".join([
                            "https://localhost/simplesaml/",
                            "saml2/idp/SingleLogoutService.php",
                        ])
                    },
                },
            },
        },
    },

    # where the remote metadata is stored
    'metadata': {
        'local': [os.path.join(SAML_BASE_DIR, 'FederationMetadata.xml')],
    },

    # set to 1 to output debugging information
    'debug': 1,

    # certificate
    'key_file': SAML_CERT_KEY_FILE,  # private part
    'cert_file': SAML_CERT_FILE,  # public part

    # own metadata settings
    'contact_person': [
        {'given_name': u'Jørgen Ulrik',
         'sur_name': 'Krag',
         'company': 'Magenta Aps',
         'email_address': 'jubk@magenta.dk',
         'contact_type': 'technical'},
        {'given_name': 'Kia',
         'sur_name': u'Jørgensen',
         'company': 'Copenhagen University',
         'email_address': 'kia@adm.ku.dk',
         'contact_type': 'administrative'},
    ],
    # you can set multilanguage information here
    'organization': {
        'name': [
            ('Copenhagen University', 'en'),
            (u'Københavns Universitet', 'da')
        ],
        'display_name': [
            ('UCPH', 'en'), ('KU', 'da')
        ],
        'url': [
            ('http://www.ku.dk/english', 'en'),
            ('http://www.ku.dk/', 'da')
        ],
    },
    'valid_for': 24,  # how long is our metadata valid
}
