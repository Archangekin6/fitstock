import datetime
from django.utils import timezone


def photo_profil(request):
    photo_url = ''
    if request.user.is_authenticated and request.user.photo_profil:
        try:
            photo_url = request.user.photo_profil.url
        except ValueError:
            photo_url = ''
    return {'photo_url': photo_url}


def alertes_globales(request):
    if not request.user.is_authenticated:
        return {}
    try:
        from .models import Produit
        today = timezone.now().date()
        SEUIL = 10
        JOURS = 7
        produits_en_alerte = list(Produit.objects.filter(utilisateur=request.user, supprime=False, quantite__lte=SEUIL).order_by('quantite')[:5])
        produits_peremption = list(Produit.objects.filter(
            utilisateur=request.user, supprime=False,
            date_expiration__isnull=False,
            date_expiration__gte=today,
            date_expiration__lte=today + datetime.timedelta(days=JOURS)
        ).order_by('date_expiration')[:5])
        alertes_count = (
            Produit.objects.filter(utilisateur=request.user, supprime=False, quantite__lte=SEUIL).count() +
            Produit.objects.filter(
                utilisateur=request.user, supprime=False,
                date_expiration__isnull=False,
                date_expiration__gte=today,
                date_expiration__lte=today + datetime.timedelta(days=JOURS)
            ).count()
        )
        return {
            'produits_en_alerte': produits_en_alerte,
            'produits_peremption': produits_peremption,
            'alertes_count': alertes_count,
        }
    except Exception:
        return {}
