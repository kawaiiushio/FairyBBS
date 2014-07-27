from django.http import HttpResponse
from forum.models import topic, post, node
from sae.storage import Bucket
import json
import random

bucket = Bucket('upload')


def topic_data(topic_id):
    t = topic.objects.get(id=topic_id)
    data=dict(id=t.id,
              title=t.title,
              content=t.content,
              create_time=t.time_created.isoformat(),
              user=dict(id=t.user.id,
                           username=t.user.username),
              reply_count=t.reply_count,
              node_id=t.node.id,
              node_name=t.node.title,
              reply_id=[p.id for p in t.post_set.all()])
    return data


def post_api(request ,post_id):
    p = post.objects.get(id=post_id)
    data = dict(id=p.id,
                content=p.content,
                topic_id=p.topic.id,
                user=dict(id=p.user.id,
                          username=p.user.username),
                create_time=p.time_created.isoformat())
    return HttpResponse(json.dumps(data))


def topics_api(request):
    data = {}
    for t in topic.objects.all()[:30]:
        data[str(t.id)] = topic_data(t.id)
    return HttpResponse(json.dumps(data))

def topic_api(request, topic_id):
    data = topic_data(topic_id)
    return HttpResponse(json.dumps(data))


def simditor_upload(request):

    def get_name(name):
        names = [i['name'] for i in bucket.list()]
        if name in names:
            return get_name(str(random.randint(1, 999))+name)
        else:
            return name

    f = request.FILES['upload_file']

    name = get_name(f.name)
    bucket.put_object(name, f)
    url = bucket.generate_url(name)

    data = {}
    data['file_path'] = url
    return HttpResponse(json.dumps(data), content_type="application/json")
