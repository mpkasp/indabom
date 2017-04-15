from django import forms

class PartInfoForm(forms.Form):
    quantity = forms.IntegerField(label='Quantity', min_value=1)