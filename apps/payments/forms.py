from django import forms
from .models import Payment


class PaymentUploadForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['reference_number', 'screenshot', 'amount']
        widgets = {
            'reference_number': forms.TextInput(attrs={
                'placeholder': 'e.g. BOP-123456789',
                'autocomplete': 'off',
                'class': 'apple-input',
            }),
            'amount': forms.HiddenInput(),
            'screenshot': forms.FileInput(attrs={
                'class': 'apple-file-input',
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        if self.course:
            self.fields['amount'].initial = self.course.price
            self.fields['reference_number'].required = True