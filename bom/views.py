import csv, export, codecs, logging

from indabom.settings import MEDIA_URL

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required

from json import loads, dumps

from .convert import full_part_number_to_broken_part
from .models import Part, PartClass, Subpart, SellerPart, Organization, PartFile
from .forms import PartInfoForm, NewPartForm, AddSubpartForm, UploadFileToPartForm, UploadSubpartsCSVForm
from .octopart_parts_match import match_part

logger = logging.getLogger(__name__)


@login_required
def home(request):
    organization, created = Organization.objects.get_or_create(
        owner=request.user,
        defaults={'name': request.user.first_name + ' ' + request.user.last_name,
                    'subscription': 'F'},
    )

    if created:
        profile = request.user.bom_profile(organization)
        profile.role = 'A'
        profile.save()

    parts = Part.objects.filter(organization=organization).order_by('number_class__code', 'number_item', 'number_variation')
    return TemplateResponse(request, 'bom/dashboard.html', locals())


@login_required
def bom_signup(request):
    user = request.user
    organization = user.bom_profile().organization
    
    if organization is not None:
        return HttpResponseRedirect('/bom/')

    return TemplateResponse(request, 'bom/bom-signup.html', locals())


@login_required
def part_info(request, part_id):
    user = request.user
    profile = user.bom_profile()
    organization = profile.organization

    parts = Part.objects.filter(id=part_id)[0].indented()
    part = Part.objects.get(id=part_id)
    if part.organization != organization:
        return HttpResponseRedirect('/bom/')

    part_info_form = PartInfoForm(initial={'quantity': 100})
    add_subpart_form = AddSubpartForm(initial={'count': 1, }, organization=organization)
    upload_file_to_part_form = UploadFileToPartForm()
    upload_subparts_csv_form = UploadSubpartsCSVForm()

    qty = 100
    if request.method == 'POST':
        part_info_form = PartInfoForm(request.POST)
        if part_info_form.is_valid():
            qty = request.POST.get('quantity', 100)

    extended_cost_complete = True
    
    unit_cost = 0
    for item in parts:
        extended_quantity = int(qty) * item['quantity']
        item['extended_quantity'] = extended_quantity

        p = item['part']
        dps = SellerPart.objects.filter(part=p)
        seller_price = None
        seller = None
        order_qty = extended_quantity
        for dp in dps:
            if dp.minimum_order_quantity < extended_quantity and (seller is None or dp.unit_cost < seller_price):
                seller_price = dp.unit_cost
                seller = dp
            elif seller is None:
                seller_price = dp.unit_cost
                seller = dp
                if dp.minimum_order_quantity > extended_quantity:
                    order_qty = dp.minimum_order_quantity

        item['seller_price'] = seller_price
        item['seller_part'] = seller
        item['order_quantity'] = order_qty
        
        # then extend that price
        item['extended_cost'] = extended_quantity * seller_price if seller_price is not None and extended_quantity is not None else None

        unit_cost = unit_cost + seller_price * item['quantity'] if seller_price is not None else unit_cost
        if seller is None:
            extended_cost_complete = False

    extended_cost = unit_cost * int(qty)

    where_used = part.where_used()
    files = part.files()
    
    return TemplateResponse(request, 'bom/part-info.html', locals())


@login_required
def export_part_indented(request, part_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="indabom_parts_indented.csv"'

    organization = request.user.bom_profile().organization
    part = Part.objects.filter(id=part_id)[0]
    if part.organization is not organization:
        return HttpResponseRedirect(request.META.get('/bom/'))

    bom = part.indented()
    qty = 100
    unit_cost = 0
    
    fieldnames = ['level', 'part_number', 'quantity', 'part_description', 'part_revision', 'part_manufacturer', 'part_manufacturer_part_number', 'part_ext_qty', 'part_order_qty', 'part_seller', 'part_cost', 'part_ext_cost']

    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for item in bom:
        extended_quantity = qty * item['quantity']
        item['extended_quantity'] = extended_quantity
        
        # then get the lowest price & seller at that quantity, 
        p = item['part']
        dps = SellerPart.objects.filter(part=p)
        seller_price = None
        seller = None
        order_qty = extended_quantity
        for dp in dps:
            if dp.minimum_order_quantity < extended_quantity and (seller is None or dp.unit_cost < seller_price):
                seller_price = dp.unit_cost
                seller = dp
            elif seller is None:
                seller_price = dp.unit_cost
                seller = dp
                if dp.minimum_order_quantity > extended_quantity:
                    order_qty = dp.minimum_order_quantity

        item['seller_price'] = seller_price
        item['seller_part'] = seller
        item['order_quantity'] = order_qty
        
        # then extend that price
        item['extended_cost'] = extended_quantity * seller_price if seller_price is not None and extended_quantity is not None else None

        unit_cost = unit_cost + seller_price * item['quantity'] if seller_price is not None else unit_cost

        row = {
        'level': item['indent_level'], 
        'part_number': item['part'].full_part_number(), 
        'quantity': item['quantity'], 
        'part_description': item['part'].description, 
        'part_revision': item['part'].revision, 
        'part_manufacturer': item['part'].manufacturer.name, 
        'part_manufacturer_part_number': item['part'].manufacturer_part_number, 
        'part_ext_qty': item['extended_quantity'],
        'part_order_qty': item['order_quantity'],
        'part_seller': item['seller_part'].seller.name if item['seller_part'] is not None else '',
        'part_cost': item['seller_price'] if item['seller_price'] is not None else 0,
        'part_ext_cost': item['extended_cost'] if item['extended_cost'] is not None else 0,
        }
        writer.writerow(row)
    return response


@login_required
def upload_part_indented(request, part_id):
    response = {
        'errors': [],
        'status': 'ok',
    }

    parts = []
    part = get_object_or_404(Part, id=part_id)
    response['part'] = part.description

    if request.method == 'POST':
        form = UploadSubpartsCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = request.FILES['file']
            dialect = csv.Sniffer().sniff(codecs.EncodedFile(csvfile, "utf-8").read(1024))
            csvfile.open()
            reader = csv.reader(codecs.EncodedFile(csvfile, "utf-8"), delimiter=',', dialect=dialect)
            headers = reader.next()

            Subpart.objects.filter(assembly_part=part).delete()

            for row in reader:
                partData = {}
                for idx, item in enumerate(row):
                    partData[headers[idx]] = item
                if 'part_number' in partData and 'quantity' in partData:
                    civ = full_part_number_to_broken_part(partData['part_number'])
                    subparts = Part.objects.filter(number_class=civ['class'], number_item=civ['item'], number_variation=civ['variation'])
                    
                    if len(subparts) == 0:
                        response['status'] = 'failed'
                        response['errors'].append('subpart: {} doesn''t exist'.format(partData['part_number']))
                        return HttpResponse(dumps(response), content_type='application/json')

                    subpart = subparts[0]
                    count = partData['quantity']
                    if part == subpart:
                        response['status'] = 'failed'
                        response['errors'].append('recursive part association: a part can''t be a subpart of itsself')
                        return HttpResponse(dumps(response), content_type='application/json')
                    sp = Subpart(assembly_part=part,assembly_subpart=subpart,count=count)
                    sp.save()
        else:
            response['status'] = 'failed'
            response['errors'].append('File form not valid: {}'.format(form.errors))
            return HttpResponse(dumps(response), content_type='application/json')
        
    response['parts'] = parts
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/bom/'))


@login_required
def upload_parts(request):
    
    # TODO: Finish this endpoint
    
    response = {
        'errors': [],
        'status': 'ok',
    }
    parts = []

    if request.POST and request.FILES:
        form = UploadSubpartsCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csvfile = request.FILES['csv_file']
            dialect = csv.Sniffer().sniff(codecs.EncodedFile(csvfile, "utf-8").read(1024))
            csvfile.open()
            reader = csv.reader(codecs.EncodedFile(csvfile, "utf-8"), delimiter=',', dialect=dialect)
            headers = reader.next()

            for row in reader:
                partData = {}
                for idx, item in enumerate(row):
                    partData[headers[idx]] = item
                parts.append(partData)

    response['parts'] = parts

    return HttpResponse(dumps(response), content_type='application/json')


@login_required
def export_part_list(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="indabom_parts.csv"'
    
    organization = request.user.bom_profile().organization
    parts = Part.objects.filter(organization=organization).order_by('number_class__code', 'number_item', 'number_variation')

    fieldnames = ['part_number', 'part_description', 'part_revision', 'part_manufacturer', 'part_manufacturer_part_number', 'part_minimum_order_quantity', 'part_minimum_pack_quantity', 'part_unit_cost']

    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for item in parts:
        row = {
        'part_number': item.full_part_number(), 
        'part_description': item.description, 
        'part_revision': item.revision, 
        'part_manufacturer': item.manufacturer.name, 
        'part_manufacturer_part_number': item.manufacturer_part_number, 
        'part_minimum_order_quantity': item.minimum_order_quantity, 
        'part_minimum_pack_quantity': item.minimum_pack_quantity,
        'part_unit_cost': item.unit_cost,
        }
        writer.writerow(row)

    return response


@login_required
def octopart_part_match(request, part_id):
    response = {
        'errors': [],
        'status': 'ok',
    }

    parts = Part.objects.filter(id=part_id)

    if len(parts) == 0:
        response['status'] = 'failed'
        response['errors'].append('no parts found with given part_id')
        return HttpResponse(dumps(response), content_type='application/json')

    seller_parts = match_part(parts[0])
    
    if len(seller_parts) > 0:
        for dp in seller_parts:
            try:
                dp.save()
            except IntegrityError:
                continue
    else:
        response['status'] = 'failed'
        response['errors'].append('octopart wasn''t able to find ant parts with given manufacturer_part_number')
        return HttpResponse(dumps(response), content_type='application/json')
        
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/bom/'))


@login_required
def octopart_part_match_indented(request, part_id):
    response = {
        'errors': [],
        'status': 'ok',
    }

    parts = Part.objects.filter(id=part_id)

    if len(parts) == 0:
        response['status'] = 'failed'
        response['errors'].append('no parts found with given part_id')
        return HttpResponse(dumps(response), content_type='application/json')

    subparts = parts[0].subparts.all()

    for part in subparts:
        seller_parts = match_part(part)
        if len(seller_parts) > 0:
            for dp in seller_parts:
                try:
                    dp.save()
                except IntegrityError:
                    continue
        
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/bom/'))


@login_required
def create_part(request):
    org = request.user.bom_profile().organization
    
    if request.method == 'POST':
        form = NewPartForm(request.POST, organization=org)
        if form.is_valid():
            new_part, created = Part.objects.get_or_create(
                number_class=form.cleaned_data['number_class'],
                number_item=form.cleaned_data['number_item'],
                number_variation=form.cleaned_data['number_variation'],
                manufacturer_part_number=form.cleaned_data['manufacturer_part_number'],
                manufacturer=form.cleaned_data['manufacturer'],
                organization=org,
                defaults={'description': form.cleaned_data['description'],
                            'revision': form.cleaned_data['revision'],
                }
            )
            return HttpResponseRedirect('/bom/' + str(new_part.id) + '/')
    else:
        form = NewPartForm(organization=org) 

    return TemplateResponse(request, 'bom/create-part.html', locals())


@login_required
def edit_part(request, part_id):
    org = request.user.bom_profile().organization
    part = Part.objects.filter(id=part_id)[0]

    if request.method == 'POST':
        form = NewPartForm(request.POST, organization=org)
        if form.is_valid():
            new_part, created = Part.objects.get_or_create(
                number_class=form.cleaned_data['number_class'],
                number_item=form.cleaned_data['number_item'],
                number_variation=form.cleaned_data['number_variation'],
                manufacturer_part_number=form.cleaned_data['manufacturer_part_number'],
                manufacturer=form.cleaned_data['manufacturer'],
                organization=org,
                defaults={'description': form.cleaned_data['description'],
                            'revision': form.cleaned_data['revision'],
                }
            )
            return HttpResponseRedirect('/bom/' + part_id + '/')
    else:
        form = NewPartForm(initial={'number_class': part.number_class,
                                'number_item': part.number_item,
                                'number_variation': part.number_variation,
                                'description': part.description,
                                'revision': part.revision,
                                'manufacturer_part_number': part.manufacturer_part_number,
                                'manufacturer': part.manufacturer,}
                                , organization=org) 

    return TemplateResponse(request, 'bom/edit-part.html', locals())


@login_required
def delete_part(request, part_id):
    part = Part.objects.filter(id=part_id)[0]
    part.delete()
    
    return HttpResponseRedirect('/bom/')


@login_required
def add_subpart(request, part_id):
    org = request.user.bom_profile().organization
    part = Part.objects.filter(id=part_id)[0]

    if request.method == 'POST':
        form = AddSubpartForm(request.POST, organization=org)
        if form.is_valid():
            new_part = Subpart.objects.create(
                assembly_part=part,
                assembly_subpart=form.cleaned_data['assembly_subpart'],
                count=form.cleaned_data['count']
            )
    
    return HttpResponseRedirect('/bom/' + part_id + '/#bom')


@login_required
def remove_subpart(request, part_id, subpart_id):
    # part = Part.objects.filter(id=part_id)[0]
    subpart = Subpart.objects.get(id=subpart_id)
    subpart.delete()
    
    return HttpResponseRedirect('/bom/' + part_id + '/#bom')


@login_required
def remove_all_subparts(request, part_id):
    # part = Part.objects.filter(id=part_id)[0]
    subparts = Subpart.objects.filter(assembly_part=part_id)
    for subpart in subparts:
        subpart.delete()
    
    return HttpResponseRedirect('/bom/' + part_id + '/#bom')


@login_required
def upload_file_to_part(request, part_id):
    if request.method == 'POST':
        form = UploadFileToPartForm(request.POST, request.FILES)
        if form.is_valid():
            part = Part.objects.get(id=part_id)
            partfile = PartFile(file=request.FILES['file'], part=part)
            partfile.save()
            return HttpResponseRedirect('/bom/' + part_id + '/')

    # TODO: Handle failed hits to this view
    return HttpResponseRedirect('/bom/' + part_id + '/')


@login_required
def delete_file_from_part(request, part_id, partfile_id):
    # part = Part.objects.filter(id=part_id)[0]
    partfile = PartFile.objects.get(id=partfile_id)
    partfile.delete()
    
    return HttpResponseRedirect('/bom/' + part_id + '/#specs')