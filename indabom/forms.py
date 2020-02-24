from django import forms
from django.contrib.auth.models import User
from captcha.fields import ReCaptchaField
from indabom.settings import DEBUG


class UserForm(forms.ModelForm):
    captcha = ReCaptchaField(label='')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['username'].required = True
        self.fields['captcha'].required = not DEBUG

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password', )
        widgets = {
            'password': forms.PasswordInput(),
        }
