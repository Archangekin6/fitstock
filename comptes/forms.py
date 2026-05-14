from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Utilisateur, Produit, Famille, EntreeStock, SortieStock, Fournisseur

class FormulaireInscription(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Utilisateur
        fields = ['username', 'email', 'password1', 'password2']

class FormulaireConnexion(AuthenticationForm):
    # AuthenticationForm gère déjà username + password
    pass

# forms.py  (ajoute ces classes dans ton fichier forms.py existant)

from django import forms
from .models import Produit, Famille


class ProduitForm(forms.ModelForm):

    class Meta:
        model = Produit
        fields = [
            # Champs communs
            'type', 'famille', 'nom', 'description',
            'quantite', 'prix', 'image',
            # Champs alimentaires uniquement
            'date_expiration', 'allergenes', 'temperature_conservation',
            # Champs matériels uniquement
            'reference', 'marque', 'garantie_mois',
        ]
        widgets = {
            'type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_type',
            }),
            'famille': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_famille',
            }),
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du produit',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description du produit...',
            }),
            'quantite': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
            }),
            'prix': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0,
                'placeholder': '0.00',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            # --- Alimentaire ---
            'date_expiration': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'allergenes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Ex : gluten, lactose, arachides...',
            }),
            'temperature_conservation': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex : entre 0°C et 4°C',
            }),
            # --- Matériel ---
            'reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Référence produit',
            }),
            'marque': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Marque',
            }),
            'garantie_mois': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Durée en mois',
            }),
        }

    def __init__(self, *args, **kwargs):
        type_produit = kwargs.pop('type_produit', None)
        super().__init__(*args, **kwargs)

        # Filtrer les familles selon le type si connu
        if type_produit:
            self.fields['famille'].queryset = Famille.objects.filter(type=type_produit)
        else:
            self.fields['famille'].queryset = Famille.objects.none()

        # Champs non obligatoires selon le type
        for field in ['date_expiration', 'allergenes', 'temperature_conservation',
                      'reference', 'marque', 'garantie_mois']:
            self.fields[field].required = False

        self.fields['famille'].required = False
        self.fields['description'].required = False
        self.fields['image'].required = False
        
        # À ajouter dans ton forms.py existant


class FamilleForm(forms.ModelForm):
    class Meta:
        model = Famille
        fields = ['nom', 'type', 'description', 'image']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de la famille',
            }),
            'type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description...',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['image'].required = False
        
        # À ajouter dans ton forms.py existant


class EntreeStockForm(forms.ModelForm):
    class Meta:
        model = EntreeStock
        fields = ['produit', 'fournisseur', 'quantite', 'prix_achat', 'date_entree', 'numero_lot', 'note']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'fournisseur': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'prix_achat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'placeholder': '0.00'}),
            'date_entree': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_lot': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: LOT-2026-001'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Remarques eventuelles...'}),
        }

    def __init__(self, *args, **kwargs):
        self.utilisateur = kwargs.pop('utilisateur', None)
        super().__init__(*args, **kwargs)
        self.fields['fournisseur'].required = False
        self.fields['numero_lot'].required = False
        self.fields['note'].required = False
        if self.utilisateur:
            self.fields['produit'].queryset = Produit.objects.filter(utilisateur=self.utilisateur, supprime=False)
            self.fields['fournisseur'].queryset = Fournisseur.objects.filter(utilisateur=self.utilisateur)


class SortieStockForm(forms.ModelForm):
    class Meta:
        model = SortieStock
        fields = ['produit', 'quantite', 'motif', 'destinataire', 'date_sortie', 'numero_reference', 'note']
        widgets = {
            'produit': forms.Select(attrs={'class': 'form-select'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'motif': forms.Select(attrs={'class': 'form-select'}),
            'destinataire': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Client, Service...'}),
            'date_sortie': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'numero_reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: REF-2026-001'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Remarques eventuelles...'}),
        }

    def __init__(self, *args, **kwargs):
        self.utilisateur = kwargs.pop('utilisateur', None)
        super().__init__(*args, **kwargs)
        self.fields['destinataire'].required = False
        self.fields['numero_reference'].required = False
        self.fields['note'].required = False
        if self.utilisateur:
            self.fields['produit'].queryset = Produit.objects.filter(utilisateur=self.utilisateur, supprime=False)

    def clean(self):
        cleaned_data = super().clean()
        produit = cleaned_data.get('produit')
        quantite = cleaned_data.get('quantite')
        if produit and quantite:
            if quantite > produit.quantite:
                raise forms.ValidationError(
                    f"Stock insuffisant. Stock disponible : {produit.quantite} unites."
                )
        return cleaned_data


# ── Widget personnalisé pour afficher le stock dans le select ──
from django.forms import Select

class ProduitSelectAvecStock(Select):
    def create_option(self, name, value, label, selected, index, subgroup=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subgroup, attrs)
        if value:
            from .models import Produit
            try:
                produit = Produit.objects.get(pk=value)
                option['attrs']['data-stock'] = produit.quantite
                option['label'] = f"{produit.nom} (stock: {produit.quantite})"
            except Produit.DoesNotExist:
                pass
        return option
    
    # À ajouter dans ton forms.py


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['nom', 'telephone', 'email', 'adresse', 'ville', 'pays']
        widgets = {
            'nom':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du fournisseur'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: +225 07 00 00 00'}),
            'email':     forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemple.com'}),
            'adresse':   forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Adresse complète...'}),
            'ville':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ville'}),
            'pays':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Pays'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ['telephone', 'email', 'adresse', 'ville', 'pays']:
            self.fields[f].required = False

# Dans SortieStockForm, remplace le widget produit par :
# 'produit': ProduitSelectAvecStock(attrs={'class': 'form-select'}),