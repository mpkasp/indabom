import csv, export

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Part

def index(request):
    # get all top level assemblies
    parts = Part.objects.all().order_by('number_class__code', 'number_item', 'number_variation')
    return render(request, 'bom/dashboard.html', {'parts': parts})

def indented(request, part_id):
    parts = Part.objects.filter(id=part_id)[0].indented()

    cost = 0
    for item in parts:
        if item['part'].unit_cost != None:
            cost = cost + item['part'].unit_cost
    
    return render(request, 'bom/indented.html', {'part_id': part_id, 'parts': parts, 'cost': cost})

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

def export_part_list(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="indabom_parts.csv"'

    parts = Part.objects.all().order_by('number_class__code', 'number_item', 'number_variation')

    fieldnames = ['part_number', 'part_description', 'part_revision', 'part_manufacturer', 'part_manufacturer_part_number', 'part_minimum_order_quantity', 'part_minimum_pack_quantity', 'part_unit_cost']

    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for item in parts:
        row = {
        'part_number': item.full_part_number(), 
        'part_description': item.description, 
        'part_revision': item.revision, 
        'part_manufacturer': item.manufacturer, 
        'part_manufacturer_part_number': item.manufacturer_part_number, 
        'part_minimum_order_quantity': item.minimum_order_quantity, 
        'part_minimum_pack_quantity': item.minimum_pack_quantity,
        'part_unit_cost': item.unit_cost,
        }
        writer.writerow(row)

    return response