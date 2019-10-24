# settings.py
import pathlib
import yaml

def get_defaults():
    return {
        'explorer': {
            'host': '127.0.0.1',
            'port': 8080,
            'secret': {'@required': True}
        },
        'nuls': {
          'base_uri': 'http://beta.wallet.nuls.io/api/',
          'chain_id': 2
        },
        'mongodb': {
          'uri': 'mongodb://127.0.0.1:27017',
          'database': 'nuls2'
        },
        'mail': {
            'email_sender': 'nuls@localhost.localdomain',
            'smtp_url': 'smtp://localhost'
        },
        'ipfs': {
            'enabled': False,
            'host': '127.0.0.1',
            'port': 5001
        },
        'aleph_client': {
            'enabled': False,
            'private_key': None,
            'api_server': 'https://api1.aleph.im',
            'channel': 'NULSWORLD'
        }
    }
