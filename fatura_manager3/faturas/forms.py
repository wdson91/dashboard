from django import forms
from .models import Profile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['photo']
        widgets = {
            'photo': forms.ClearableFileInput(attrs={'multiple': False}),
        }