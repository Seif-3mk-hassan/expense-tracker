from django import forms
from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class ProfileForm(forms.ModelForm):
    CURRENCIES = [
        ("EGP", "EGP - Egyptian Pound"),
        ("USD", "USD - US Dollar"),
        ("EUR", "EUR - Euro"),
    ]
    currency = forms.ChoiceField(choices=CURRENCIES)

    class Meta:
        model = Profile
        fields = ["currency", "month_start_day"]
