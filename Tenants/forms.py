from django import forms
from .models import Utilisateur

class UtilisateurInlineForm(forms.ModelForm):
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, required=False)

    class Meta:
        model = Utilisateur
        fields = '__all__'

class UtilisateurCreationForm(forms.ModelForm):
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput, required=False)
    username = forms.CharField(label="Pseudo", required=False, help_text="Laisser vide pour générer automatiquement")

    class Meta:
        model = Utilisateur
        fields = '__all__'
        exclude = ('groups', 'user_permissions', 'last_token', 'date_joined', 'last_login', 'is_staff', 'is_superuser', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['statut'].initial = True

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
