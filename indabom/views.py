from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.template.response import TemplateResponse
from django.db import IntegrityError

from django.contrib.auth.models import User
from forms import UserForm

def index(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect('/bom/')
    else:
        return TemplateResponse(request, 'indabom/index.html', locals())

def signup(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            new_user = User.objects.create_user(**form.cleaned_data)
            login(request, new_user)
            return HttpResponseRedirect('/bom/')
    else:
        form = UserForm() 

    return TemplateResponse(request, 'indabom/signup.html', locals())