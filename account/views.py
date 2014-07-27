#encoding=utf-8
from PIL import Image
from account.models import profile, social
from django.contrib import auth
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.views import password_reset, password_reset_confirm
from django.core.context_processors import csrf
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from fairy import conf
from forum.models import topic, post, node
from forum.views import error
import json
import markdown
import os
import shutil
import tempfile
import urllib
import urllib2
import re
import random
import sae.kvdb
from sae.storage import Bucket
from sae.ext.storage import monkey

kv = sae.kvdb.KVClient()
avatar_bucket = Bucket('avatar')
monkey.patch_all()

try:
    from StringIO import StringIO
except ImportError:
    from cStringIO import StringIO

alphanumeric = RegexValidator(r'^[0-9a-zA-Z\_]*$', 'Only alphanumeric characters and underscore are allowed.')


def user_info(request, user_id):
    u = User.objects.get(id=user_id)

    if not profile.objects.filter(user_id=u.id).exists():
        p = profile()
        p.user = u
        p.save()

    return render_to_response('account/user-info.html', {'request': request, 'title': _('user info'),
                                                 'user': u, 'conf': conf,
                                                 'topics': u.profile.latest_activity()['topic'],
                                                 'post_list_title': _('%s\'s topics') % (u.profile.username())})



def reg(request):
    if request.method == 'GET':
        return render_to_response('account/reg.html', {'conf': conf, 'title': _('register')},
                                  context_instance=RequestContext(request))
    elif request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password2 = request.POST['password2']

        try:
            alphanumeric(username)
        except:
            messages.add_message(request, messages.WARNING,_('username can only contain letters digits and underscore'))
            return HttpResponseRedirect(reverse('reg'))

        if User.objects.filter(username=username).exists():
            messages.add_message(request, messages.WARNING, _('username already exists'))
            return HttpResponseRedirect(reverse('reg'))

        if password != password2 or password == '' or password2 == '':
            messages.add_message(request, messages.WARNING, _('passwords don\'t match, or are blank'))
            return HttpResponseRedirect(reverse('reg'))

        user = User.objects.create_user(username, email, password)

        if user.id == 1:
            user.is_staff = True
            user.is_superuser = True
            user.save()

        user = authenticate(username=username, password=password)
        login(request, user)
        p = profile()
        p.user = user
        p.save()
        return HttpResponseRedirect(reverse('index'))


def user_login(request):
    if request.method == 'GET':
        return render_to_response('account/login.html', {'conf': conf, 'title': _('sign in')},
                                  context_instance=RequestContext(request))
    elif request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        
        if not User.objects.filter(username=username).exists():
            messages.add_message(request, messages.WARNING, _('username does not exist'))
            return HttpResponseRedirect(reverse('signin'))

        if user is None:
            messages.add_message(request, messages.WARNING, _('password is invalid'))
            return HttpResponseRedirect(reverse('signin'))

        login(request, user)
        return HttpResponseRedirect(reverse('index'))


def setting(request):
    if request.method == 'GET':
        return render_to_response('account/user-setting.html', {'request': request,
                                                        'conf': conf,
                                                        'title': _('settings')},
                                  context_instance=RequestContext(request))
    elif request.method == 'POST':
        request.user.profile.website = request.POST['website']
        request.user.email = request.POST['email']
        request.user.profile.save()
        request.user.save()
        return render_to_response('account/user-setting.html', {'request': request,
                                                        'conf': conf,
                                                        'title': _('settings')},
                                  context_instance=RequestContext(request))


def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))


def view_mention(request):
    old = request.user.profile.old_mention()
    new = request.user.profile.unread_mention()
    for m in new:
        m.read = True
        m.save()
    return render_to_response('account/user-mention.html', {'request': request, 'title': _('mentions'),
                                                    'conf': conf,
                                                    'new': new,
                                                    'old': old, },
                              context_instance=RequestContext(request))


def change_password(request):
    u = request.user
    if request.method == 'GET':
        return render_to_response('account/change-password.html', {'request': request, 'title': _('change password'),
                                                           'conf': conf},
                                  context_instance=RequestContext(request))
    elif request.method == 'POST':
        old = request.POST['old-password']
        new = request.POST['password']
        if request.POST['password'] != request.POST['password2'] or request.POST['password'] == '' or request.POST['password2'] == '':
            messages.add_message(request, messages.WARNING, _('passwords don\'t match, or are blank'))
            return HttpResponseRedirect(reverse('change_password'))

        if authenticate(username=u.username, password=old):
            u.set_password(new)
            u.save()
            messages.add_message(request, messages.SUCCESS, _('password updated successfully'))
            return HttpResponseRedirect(reverse('change_password'))
        else:
            messages.add_message(request, messages.WARNING, _('unable to change your password, the current password may be invalid'))
            return HttpResponseRedirect(reverse('change_password'))


def user_avatar(request):
    u = request.user
    if request.method == 'GET':
        return render_to_response('account/user-avatar.html', {'request': request, 'title': _('Avatar Settings'),
                                                       'conf': conf},
                                  context_instance=RequestContext(request))
    else:
        use_gravatar = request.POST.getlist('gravatar') == ['true']
        request.user.profile.use_gravatar = use_gravatar
        f = request.FILES.get('file', None)
        if f:
            extension = os.path.splitext(f.name)[-1]
            if f.size > 524288:
                return error(request, _('File too big'))
            if (extension not in ['.jpg', '.png', '.gif']) or ('image' not in f.content_type):
                return error(request, _('File type not allowed'))
            im = Image.open(f)
            im.thumbnail((120,120))
            name = str(u.id) + '.png'
            temp = StringIO()
            im.save(temp, 'PNG')
            avatar_bucket.put_object(name, temp.getvalue())
            temp.close()
            url = avatar_bucket.generate_url(name)
            u.profile.avatar_url = url
        u.profile.save()
        return HttpResponseRedirect(reverse('user_avatar'))


def reset_confirm(request, uidb64=None, token=None):
    return password_reset_confirm(request, template_name='account/reset-password-confirm.html',
        uidb64=uidb64, token=token, post_reset_redirect=reverse('signin'))


def reset(request):
    return password_reset(request, template_name='account/reset-password.html',
        email_template_name='account/reset-password-email.html',
        subject_template_name='account/reset-password-subject.txt',
        post_reset_redirect=reverse('signin'))