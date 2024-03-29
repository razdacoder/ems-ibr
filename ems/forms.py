from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    email = forms.EmailField()
    password = forms.CharField(min_length=8)
