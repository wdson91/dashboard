from django import forms
from django.contrib.auth.models import User

class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(label="Nome", required=False)
    last_name = forms.CharField(label="Sobrenome", required=False)
    email = forms.EmailField(label="Email")

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']



