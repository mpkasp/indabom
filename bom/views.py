import csv, export

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

    bom = Part.objects.filter(id=part_id)[0].indented()

    fieldnames = ['level', 'part_number', 'part_description', 'part_revision', 'quantity', 'part_manufacturer', 'part_manufacturer_part_number', 'part_minimum_order_quantity', 'part_minimum_pack_quantity', 'part_unit_cost']

    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for item in bom:
        row = {
        'level': item['indent_level'], 
        'part_number': item['part'].full_part_number(), 
        'part_description': item['part'].description, 
        'part_revision': item['part'].revision, 
        'quantity': item['quantity'], 
        'part_manufacturer': item['part'].manufacturer, 
        'part_manufacturer_part_number': item['part'].manufacturer_part_number, 
        'part_minimum_order_quantity': item['part'].minimum_order_quantity, 
        'part_minimum_pack_quantity': item['part'].minimum_pack_quantity,
        'part_unit_cost': item['part'].unit_cost,
        }
        writer.writerow(row)

    return response