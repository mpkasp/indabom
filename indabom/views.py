from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, get_user_model
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic.base import TemplateView

from indabom.settings import DEBUG
from indabom.forms import UserForm

from urllib.error import URLError


def index(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('bom:home'))
    else:
        return TemplateResponse(request, 'indabom/index.html', locals())


def handler404(request, exception=None):
    return render(request, 'indabom/404.html', status=404)


def handler500(request):
    return render(request, 'indabom/500.html', status=500)


def signup(request):
    name = 'signup'
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        try:
            if form.is_valid():
                new_user = form.save()
                login(request, new_user, backend='django.contrib.auth.backends.ModelBackend')
                return HttpResponseRedirect(reverse('bom:home'))
        except URLError:
            if DEBUG and len(form.errors.keys()) == 1 and 'captcha' in form.errors.keys():
                new_user = form.save()
                login(request, new_user, backend='django.contrib.auth.backends.ModelBackend')
                return HttpResponseRedirect(reverse('bom:home'))
    else:
        form = UserForm()

    return TemplateResponse(request, 'indabom/signup.html', locals())


class About(TemplateView):
    name = 'about'
    template_name = f'indabom/{name}.html'

    def get_context_data(self, *args, **kwargs):
        context = super(About, self).get_context_data(**kwargs)
        context['name'] = self.name
        return context


class LearnMore(TemplateView):
    name = 'learn-more'
    template_name = f'indabom/{name}.html'

    def get_context_data(self, *args, **kwargs):
        context = super(LearnMore, self).get_context_data(**kwargs)
        context['name'] = self.name
        return context


class PrivacyPolicy(TemplateView):
    name = 'privacy-policy'
    template_name = f'indabom/{name}.html'

    def get_context_data(self, *args, **kwargs):
        context = super(PrivacyPolicy, self).get_context_data(**kwargs)
        context['name'] = self.name
        return context


class Install(TemplateView):
    name = 'install'
    template_name = f'indabom/{name}.html'

    def get_context_data(self, *args, **kwargs):
        context = super(Install, self).get_context_data(**kwargs)
        context['name'] = self.name
        return context
