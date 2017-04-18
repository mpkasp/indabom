from django import forms
from django.contrib.auth.models import User

class UserForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['username'].required = True
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password', )
        widgets = {
            'password': forms.PasswordInput(),
        }