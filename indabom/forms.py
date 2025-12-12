from bom.models import Organization
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django_recaptcha.fields import ReCaptchaField

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
    organization = forms.ModelChoiceField(queryset=Organization.objects.none(), widget=forms.HiddenInput())
    unit = forms.IntegerField(min_value=1)
    renewal_consent_text = "I understand and agree that my subscription will automatically renew each month at the current rate unless canceled."
    renewal_consent = forms.BooleanField(required=True, label=renewal_consent_text)

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner')
        super(SubscriptionForm, self).__init__(*args, **kwargs)
        queryset = Organization.objects.filter(owner=self.owner)
        self.fields['organization'].queryset = queryset
        if queryset.count() > 0:
            self.fields['organization'].initial = queryset[0]


class OrganizationForm(forms.Form):
    organization = forms.ModelChoiceField(queryset=Organization.objects.none())

    def __init__(self, *args, **kwargs):
        self.owner = kwargs.pop('owner')
        super(OrganizationForm, self).__init__(*args, **kwargs)
        self.fields['organization'].queryset = Organization.objects.filter(owner=self.owner)


class PasswordConfirmForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label='Confirm your password')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean_password(self):
        pwd = self.cleaned_data.get('password')
        if not self.user.check_password(pwd):
            raise ValidationError('Incorrect password.')
        return pwd