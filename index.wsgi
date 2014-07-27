import sae
import json
from fairy import wsgi
from django.core.management import call_command
import sae.kvdb

kv = sae.kvdb.KVClient()

key = 'fairybbs_installed'

if kv.get(key) == None:
    try:
        call_command('syncdb', interactivate=False)
    except:
        pass
    kv.set(key, '1')
    kv.set('conf_sitename', 'FairyBBS(SAE)')
    kv.set('conf_logoname', 'FairyBBS')
    kv.set('conf_links', json.dumps({'FairyBBS': 'http://fairybbs.com'}))

application = sae.create_wsgi_app(wsgi.application)