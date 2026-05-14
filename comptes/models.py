from django.contrib.auth.models import AbstractUser
from django.db import models
import random


class Utilisateur(AbstractUser):
    email_verifie      = models.BooleanField(default=False)
    code_verification  = models.CharField(max_length=6, blank=True)
    photo_profil       = models.ImageField(upload_to='profils/', null=True, blank=True)
    nom_entreprise     = models.CharField(max_length=100, blank=True)
    adresse_entreprise = models.TextField(blank=True)
    telephone_entreprise = models.CharField(max_length=20, blank=True)

    def generer_code(self):
        self.code_verification = str(random.randint(100000, 999999))
        self.save()
        return self.code_verification


class Famille(models.Model):

    TYPE_CHOICES = [
        ('alimentaire', 'Alimentaire'),
        ('non_alimentaire', 'Non alimentaire'),
    ]

    utilisateur = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, null=True, blank=True)
    nom         = models.CharField(max_length=100)
    type        = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True)
    image       = models.ImageField(upload_to='familles/', null=True, blank=True)
    date_ajout  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_type_display()}] {self.nom}"

    class Meta:
        verbose_name        = "Famille"
        verbose_name_plural = "Familles"
        ordering            = ['nom']


class Produit(models.Model):

    TYPE_CHOICES = [
        ('alimentaire', 'Alimentaire'),
        ('non_alimentaire', 'Non alimentaire'),
    ]

    type                     = models.CharField(max_length=20, choices=TYPE_CHOICES)
    utilisateur              = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, null=True, blank=True)
    famille                  = models.ForeignKey(Famille, on_delete=models.SET_NULL, null=True, blank=True)
    image                    = models.ImageField(upload_to='produits/', null=True, blank=True)
    code_produit             = models.CharField(max_length=20, unique=True, blank=True)
    nom                      = models.CharField(max_length=100)
    description              = models.TextField(blank=True)
    quantite                 = models.PositiveIntegerField(default=0)
    prix                     = models.DecimalField(max_digits=10, decimal_places=2)
    date_ajout               = models.DateTimeField(auto_now_add=True)
    date_modification        = models.DateTimeField(auto_now=True)
    date_expiration          = models.DateField(null=True, blank=True)
    allergenes               = models.TextField(blank=True)
    temperature_conservation = models.CharField(max_length=50, blank=True)
    reference                = models.CharField(max_length=50, blank=True)
    marque                   = models.CharField(max_length=50, blank=True)
    garantie_mois            = models.PositiveIntegerField(null=True, blank=True)
    supprime                 = models.BooleanField(default=False)
    date_suppression         = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code_produit:
            prefix = 'ALI' if self.type == 'alimentaire' else 'MAT'
            import uuid
            self.code_produit = f"{prefix}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.get_type_display()}] {self.nom}"

    class Meta:
        verbose_name        = "Produit"
        verbose_name_plural = "Produits"
        ordering            = ['-date_ajout']


class EntreeStock(models.Model):
    produit     = models.ForeignKey('Produit', on_delete=models.CASCADE, related_name='entrees')
    fournisseur = models.ForeignKey('Fournisseur', on_delete=models.SET_NULL, null=True, blank=True)
    quantite    = models.PositiveIntegerField()
    prix_achat  = models.DecimalField(max_digits=10, decimal_places=2)
    date_entree = models.DateField()
    numero_lot  = models.CharField(max_length=50, blank=True)
    note        = models.TextField(blank=True)
    date_ajout  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Entrée {self.produit.nom} – {self.quantite} unités le {self.date_entree}"

    class Meta:
        verbose_name        = "Entrée stock"
        verbose_name_plural = "Entrées stock"
        ordering            = ['-date_entree']


class SortieStock(models.Model):

    MOTIF_CHOICES = [
        ('vente',         'Vente'),
        ('consommation',  'Consommation interne'),
        ('perte',         'Perte / Périmé'),
        ('retour',        'Retour fournisseur'),
        ('autre',         'Autre'),
    ]

    produit           = models.ForeignKey('Produit', on_delete=models.CASCADE, related_name='sorties')
    quantite          = models.PositiveIntegerField()
    motif             = models.CharField(max_length=20, choices=MOTIF_CHOICES)
    destinataire      = models.CharField(max_length=100, blank=True)
    date_sortie       = models.DateField()
    numero_reference  = models.CharField(max_length=50, blank=True)
    note              = models.TextField(blank=True)
    date_ajout        = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sortie {self.produit.nom} – {self.quantite} unités le {self.date_sortie}"

    class Meta:
        verbose_name        = "Sortie stock"
        verbose_name_plural = "Sorties stock"
        ordering            = ['-date_sortie']


class Fournisseur(models.Model):
    utilisateur = models.ForeignKey('Utilisateur', on_delete=models.CASCADE, null=True, blank=True)
    nom        = models.CharField(max_length=100)
    telephone  = models.CharField(max_length=20, blank=True)
    email      = models.EmailField(blank=True)
    adresse    = models.TextField(blank=True)
    ville      = models.CharField(max_length=100, blank=True)
    pays       = models.CharField(max_length=100, blank=True)
    date_ajout = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom

    class Meta:
        verbose_name        = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
        ordering            = ['nom']