import csv

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Part

def index(request):
    # get all top level assemblies
    top_level_assys = Part.objects.filter(number_class__code=100)
    return render(request, 'bom/dashboard.html', {'top_level_assemblies': top_level_assys})

def export_part_indented(request, part_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="indabom_parts_indented.csv"'

    tlp = Part.objects.filter(id=part_id)

    writer = csv.writer(response)
    writer.writerow(['level', 'part number', 'revision', 'description'])

    # TODO: iterate over part and subparts, etc, and export to CSV
    writer.writerow(['1', tlp.full_part_number(), tlp.revision, tlp.description])

    return response