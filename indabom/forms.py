from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from captcha.fields import ReCaptchaField

from bom.models import Organization
from indabom.settings import DEBUG


class UserForm(UserCreationForm):
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['captcha'].required = not DEBUG
        if DEBUG:
            del self.fields['captcha']

    def clean_email(self):
        email = self.cleaned_data['email']
        exists = User.objects.filter(email__iexact=email).count() > 0
        if exists:
            raise ValidationError('An account with this email address already exists.')
        return email

    def save(self, commit=True):
        user = super(UserForm, self).save(commit=commit)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user


class SubscriptionForm(forms.Form):
    price_id = forms.CharField(widget=forms.HiddenInput(), max_length=255)
    organization = forms.ModelChoiceField(queryset=Organization.objects.none())
    additional_users = forms.IntegerField(min_value=0)

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner')
        super(SubscriptionForm, self).__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.filter(owner=self.owner)
