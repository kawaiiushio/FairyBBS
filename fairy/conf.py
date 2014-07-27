#encoding=utf-8
from account.models import profile
from fairy import settings
from forum.models import node, topic, post
import os
import sae.kvdb
import json

kv = sae.kvdb.KVClient()

sitename = kv.get('conf_sitename')
logoname = kv.get('conf_logoname')

links = json.loads(kv.get('conf_links'))
nodes = node.objects.all()
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_PATH = os.path.join(BASE_DIR, 'static/upload')
user_count = profile.objects.count()
topic_count = topic.objects.count()
post_count = post.objects.count()

site_off = False