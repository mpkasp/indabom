from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, get_user_model
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic.base import TemplateView

from indabom.settings import DEBUG
from indabom.forms import UserForm

from urllib.request import URLError


def index(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('bom:home'))
    else:
        return TemplateResponse(request, 'indabom/index.html', locals())


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
            if DEBUG:
                new_user = get_user_model().objects.create_user(**form.cleaned_data)
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
