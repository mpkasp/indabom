from __future__ import unicode_literals

from django.db import models
from django.core.validators import MaxValueValidator
from indabom.settings import MEDIA_ROOT

class PartClass(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=255, default=None)
    comment = models.CharField(max_length=255, default=None, blank=True)

    def __unicode__(self):
        return u'%s' % (self.code)

class Manufacturer(models.Model):
    name = models.CharField(max_length=128, default=None)

# Numbering scheme is hard coded for now, may want to change this to a setting depending on a part numbering scheme
class Part(models.Model):
    number_class = models.ForeignKey(PartClass, default=None, related_name='number_class')
    number_item = models.CharField(max_length=4, default=None, blank=True)
    number_variation = models.CharField(max_length=2, default=None, blank=True)
    description = models.CharField(max_length=255, default=None)
    revision = models.CharField(max_length=2)
    manufacturer_part_number = models.CharField(max_length=128, default='', blank=True)
    manufacturer = models.ForeignKey(Manufacturer, default=None, blank=True, null=True)
    subparts = models.ManyToManyField('self', blank=True, symmetrical=False, through='Subpart', through_fields=('assembly_part', 'assembly_subpart'))

    class Meta():
        unique_together = ['number_class', 'number_item', 'number_variation']

    def full_part_number(self):
        return "{0}-{1}-{2}".format(self.number_class.code,self.number_item,self.number_variation)

    def distributor_parts(self):
        return DistributorPart.objects.filter(part=self).order_by('distributor', 'minimum_order_quantity')

    def seller_parts(self):
        return SellerPart.objects.filter(part=self).order_by('seller', 'minimum_order_quantity')

    def where_used(self):
        used_in_subparts = Subpart.objects.filter(assembly_subpart=self)
        used_in_parts = [subpart.assembly_part for subpart in used_in_subparts]
        return used_in_parts

    def files(self):
        partfiles = PartFile.objects.filter(part=self)
        files = [partfile.file for partfile in partfiles]
        return files   

    def indented(self):
        def indented_given_bom(bom, part, qty=1, indent_level=0):
            bom.append({
                'part': part,
                'quantity': qty,
                'indent_level': indent_level
                })
            
            indent_level = indent_level + 1
            if(len(part.subparts.all()) == 0):
                return
            else:
                for sp in part.subparts.all():
                    qty = Subpart.objects.get(assembly_part=part, assembly_subpart=sp).count
                    indented_given_bom(bom, sp, qty, indent_level)

        bom = []
        cost = 0
        indented_given_bom(bom, self)
        return bom

    def save(self):
        if self.number_item is None or self.number_item == '':
            last_number_item = Part.objects.all().filter(number_class=self.number_class).order_by('number_item').last()
            if not last_number_item:
                self.number_item = '0001'
            else:
                self.number_item = "{0:0=4d}".format(int(last_number_item.number_item) + 1)
        if self.number_variation is None or self.number_variation == '':
            last_number_variation = Part.objects.all().filter(number_class=self.number_class, number_item=self.number_item).order_by('number_variation').last()
            if not last_number_variation:
                self.number_variation = '01'
            else:
                self.number_variation = "{0:0=2d}".format(int(last_number_variation.number_variation) + 1)
        if self.manufacturer_part_number == '' and self.manufacturer is None:
            self.manufacturer_part_number = self.full_part_number()
            self.manufacturer = Manufacturer.objects.get(name='ATLAS WEARABLES')
        super(Part, self).save()

class Subpart(models.Model):
    assembly_part = models.ForeignKey(Part, related_name='assembly_part', null=True)
    assembly_subpart = models.ForeignKey(Part, related_name='assembly_subpart', null=True)
    count = models.IntegerField(default=1)

    def combine_similar(self):
        sps = Subpart.objects.filter(assembly_part=self.assembly_part, assembly_subpart=self.assembly_subpart)
        if len(sps) > 0:
            sps[0].count += int(self.count)
            return
        else:
            self.save()

class Seller(models.Model):
    name = models.CharField(max_length=128, default=None)

class SellerPart(models.Model):
    seller = models.ForeignKey(Seller)
    part = models.ForeignKey(Part)
    minimum_order_quantity = models.IntegerField(null=True, blank=True)
    minimum_pack_quantity = models.IntegerField(null=True, blank=True)
    unit_cost = models.DecimalField(null=True, max_digits=8, decimal_places=4, blank=True)
    lead_time_days = models.IntegerField(null=True, blank=True)
    nre_cost = models.DecimalField(null=True, max_digits=8, decimal_places=4, blank=True)
    ncnr = models.BooleanField(default=False)

    class Meta():
        unique_together = ['seller', 'part', 'minimum_order_quantity', 'unit_cost']

class PartFile(models.Model):
    file = models.FileField(upload_to=MEDIA_ROOT + '/partfiles')
    upload_date = models.DateField(auto_now=True)
    part = models.ForeignKey(Part)
