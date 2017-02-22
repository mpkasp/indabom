from __future__ import unicode_literals

from django.db import models
from django.core.validators import MaxValueValidator

class PartClass(models.Model):
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=255, default=None)
    comment = models.CharField(max_length=255, default=None, blank=True)

    def __unicode__(self):
        return u'%s' % (self.code)

# Numbering scheme is hard coded for now, may want to change this to a setting depending on a part numbering scheme
class Part(models.Model):
    number_class = models.ForeignKey(PartClass, default=None, related_name='number_class')
    number_item = models.CharField(max_length=4, default=None, blank=True)
    number_variation = models.CharField(max_length=2, default=None, blank=True)
    description = models.CharField(max_length=255, default=None)
    revision = models.CharField(max_length=2)
    manufacturer_part_number = models.CharField(max_length=128, default='', blank=True)
    manufacturer = models.CharField(max_length=128, default=None, blank=True)
    subparts = models.ManyToManyField('self', blank=True, symmetrical=False, through='Subpart', through_fields=('assembly_part', 'assembly_subpart'))
    minimum_order_quantity = models.IntegerField(null=True, blank=True)
    minimum_pack_quantity = models.IntegerField(null=True, blank=True)
    unit_cost = models.DecimalField(null=True, max_digits=8, decimal_places=4, blank=True)

    class Meta():
        unique_together = (('number_class', 'number_item', 'number_variation')),

    def atlas_part_number(self):
        return "{0}-{1}-{2}".format(self.number_class.code,self.number_item,self.number_variation)

    def save(self):
        if self.number_item is None or self.number_item == '':
            last_number_item = Part.objects.all().order_by('number_item').last()
            if not last_number_item:
                self.number_item = '0001'
            else:
                self.number_item = "{0:0=4d}".format(int(last_number_item.number_item) + 1)
        if self.number_variation is None or self.number_variation == '':
            last_number_variation = Part.objects.all().filter(number_item=self.number_item).order_by('number_variation').last()
            if not last_number_variation:
                self.number_variation = '01'
            else:
                self.number_variation = "{0:0=2d}".format(int(last_number_variation.number_variation) + 1)
        super(Part, self).save()

class Subpart(models.Model):
    assembly_part = models.ForeignKey(Part, related_name='assembly_part', null=True)
    assembly_subpart = models.ForeignKey(Part, related_name='assembly_subpart', null=True)
    count = models.IntegerField(default=1)