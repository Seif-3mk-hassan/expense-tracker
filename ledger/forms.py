from django import forms

from .models import Category, Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["amount", "category", "date", "payment", "note"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["category"].queryset = (
                Category.objects.for_user(user).filter(active=True)
            )


class ImportForm(forms.Form):
    file = forms.FileField(
        help_text="A JSON file in the Xpens export shape.", label="JSON file"
    )

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if uploaded.size > 2 * 1024 * 1024:
            raise forms.ValidationError("File is larger than 2 MB.")
        if not uploaded.name.endswith(".json"):
            raise forms.ValidationError("Only .json files are accepted.")
        return uploaded
