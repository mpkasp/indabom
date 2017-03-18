from django.shortcuts import render, get_object_or_404
from django.contrib.auth import authenticate, login
from django.template.response import TemplateResponse
from django.db import IntegrityError

def index(request):
    return TemplateResponse(request, 'indabom/index.html', locals())