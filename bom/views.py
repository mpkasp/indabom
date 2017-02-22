from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Part

def index(request):
    assembly = get_object_or_404(Part, pk=1)
    return render(request, 'bom/dashboard.html', {'assembly': assembly})