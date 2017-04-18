from django import forms

from .models import Part

class PartInfoForm(forms.Form):
    quantity = forms.IntegerField(label='Quantity', min_value=1)

class NewPartForm(forms.ModelForm):   
    class Meta:
        model = Part
        fields = ('number_class', 'description', 'revision', 'manufacturer_part_number', 'manufacturer', )