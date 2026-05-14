from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.db import models as django_models
from .forms import FormulaireInscription, FormulaireConnexion, ProduitForm, EntreeStockForm
from .models import Utilisateur, Produit, Famille, EntreeStock
from .forms import FamilleForm, FournisseurForm
from .models import Fournisseur
from .models import SortieStock
from .forms import SortieStockForm
import random
import datetime
import requests
from django.contrib import messages
from django.db.models import Sum, F
from django.db.models.functions import TruncMonth
import json


MOIS_FR = [
    '', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
]


def inscription(request):
    if request.method == 'POST':
        form = FormulaireInscription(request.POST)
        if form.is_valid():
            user = Utilisateur.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1'],
            )
            user.email_verifie = True
            user.save()
            login(request, user)
            return redirect('accueil')
    else:
        form = FormulaireInscription()
    return render(request, 'inscription.html', {'form': form})


def verifier_email(request):
    data         = request.session.get('inscription_data')
    code_session = request.session.get('code_verification')
    expiration   = request.session.get('code_expiration')

    if not data or not code_session:
        return redirect('inscription')

    if expiration and timezone.now().timestamp() > float(expiration):
        request.session.pop('inscription_data', None)
        request.session.pop('code_verification', None)
        request.session.pop('code_expiration', None)
        return render(request, 'verifier_email.html', {
            'erreur': 'Le code a expiré. Veuillez vous réinscrire.',
            'email': data.get('email', ''),
            'expire': True,
        })

    erreur = None
    if request.method == 'POST':
        code_saisi = request.POST.get('code', '').strip()
        if code_saisi == code_session:
            user = Utilisateur.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
            )
            user.email_verifie = True
            user.save()
            request.session.pop('inscription_data', None)
            request.session.pop('code_verification', None)
            request.session.pop('code_expiration', None)
            login(request, user)
            return redirect('accueil')
        else:
            erreur = 'Code incorrect, réessayez.'

    return render(request, 'verifier_email.html', {
        'erreur': erreur,
        'email': data.get('email', ''),
    })


def renvoyer_code(request):
    data = request.session.get('inscription_data')
    if not data:
        return redirect('inscription')
    code = str(random.randint(100000, 999999))
    request.session['code_verification'] = code
    request.session['code_expiration']   = str(timezone.now().timestamp() + 600)
    try:
        send_mail(
            subject='Nouveau code de vérification',
            message=f"Votre nouveau code est : {code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[data['email']],
        )
    except Exception:
        pass
    return redirect('verifier_email')


def connexion(request):
    if request.method == 'POST':
        form = FormulaireConnexion(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if not user.email_verifie:
                code = str(random.randint(100000, 999999))
                request.session['inscription_data']  = {
                    'username': user.username,
                    'email':    user.email,
                    'password': '',
                }
                request.session['code_verification'] = code
                request.session['code_expiration']   = str(timezone.now().timestamp() + 600)
                request.session['user_id_existant']  = user.id
                send_mail(
                    subject='Votre code de vérification',
                    message=f"Votre code de vérification est : {code}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                )
                return redirect('verifier_email')
            login(request, user)
            return redirect('accueil')
    else:
        form = FormulaireConnexion()
    return render(request, 'connexion.html', {'form': form})


def deconnexion(request):
    logout(request)
    return redirect('connexion')


def accueil(request):
    today        = timezone.now().date()
    u            = request.user
    SEUIL_ALERTE = 10
    JOURS_PEREMPTION = 7

    # KPI — filtrés par utilisateur
    total_produits = Produit.objects.filter(utilisateur=u, supprime=False).count()
    valeur_stock   = Produit.objects.filter(utilisateur=u, supprime=False).aggregate(v=Sum(F('quantite') * F('prix')))['v'] or 0
    produits_sortis = SortieStock.objects.filter(
        produit__utilisateur=u,
        date_sortie__month=today.month, date_sortie__year=today.year
    ).aggregate(t=Sum('quantite'))['t'] or 0

    mois_prec  = today.month - 1 or 12
    annee_prec = today.year if today.month > 1 else today.year - 1
    total_prec = Produit.objects.filter(utilisateur=u, date_ajout__month=mois_prec, date_ajout__year=annee_prec).count()
    total_mois = Produit.objects.filter(utilisateur=u, date_ajout__month=today.month, date_ajout__year=today.year).count()
    trend_produits = round(((total_mois - total_prec) / total_prec * 100) if total_prec else 0)

    sortis_prec  = SortieStock.objects.filter(produit__utilisateur=u, date_sortie__month=mois_prec, date_sortie__year=annee_prec).aggregate(t=Sum('quantite'))['t'] or 0
    trend_sortis = round(((produits_sortis - sortis_prec) / sortis_prec * 100) if sortis_prec else 0)

    produits_en_alerte  = Produit.objects.filter(utilisateur=u, supprime=False, quantite__lte=SEUIL_ALERTE).order_by('quantite')
    limite_peremption   = today + datetime.timedelta(days=JOURS_PEREMPTION)
    produits_peremption = Produit.objects.filter(
        utilisateur=u, supprime=False,
        date_expiration__isnull=False,
        date_expiration__gte=today,
        date_expiration__lte=limite_peremption
    ).order_by('date_expiration')
    alertes_count = produits_en_alerte.count() + produits_peremption.count()

    dernieres_entrees = EntreeStock.objects.filter(produit__utilisateur=u).select_related('produit', 'fournisseur').order_by('-date_entree')[:5]
    dernieres_sorties = SortieStock.objects.filter(produit__utilisateur=u).select_related('produit').order_by('-date_sortie')[:5]

    import calendar
    nb_jours = calendar.monthrange(today.year, today.month)[1]
    graph_labels  = [str(j) for j in range(1, nb_jours + 1)]

    entrees_mois = EntreeStock.objects.filter(produit__utilisateur=u, date_entree__month=today.month, date_entree__year=today.year).values('date_entree__day').annotate(total=Sum('quantite'))
    sorties_mois = SortieStock.objects.filter(produit__utilisateur=u, date_sortie__month=today.month, date_sortie__year=today.year).values('date_sortie__day').annotate(total=Sum('quantite'))
    entrees_dict = {e['date_entree__day']: e['total'] for e in entrees_mois}
    sorties_dict = {s['date_sortie__day']: s['total'] for s in sorties_mois}
    graph_entrees = [entrees_dict.get(j, 0) for j in range(1, nb_jours + 1)]
    graph_sorties = [sorties_dict.get(j, 0) for j in range(1, nb_jours + 1)]

    return render(request, 'accueil.html', {
        'total_produits':      total_produits,
        'valeur_stock':        valeur_stock,
        'produits_sortis':     produits_sortis,
        'alertes_count':       alertes_count,
        'trend_produits':      trend_produits,
        'trend_sortis':        trend_sortis,
        'produits_en_alerte':  produits_en_alerte,
        'produits_peremption': produits_peremption,
        'seuil_alerte':        SEUIL_ALERTE,
        'jours_peremption':    JOURS_PEREMPTION,
        'dernieres_entrees':   dernieres_entrees,
        'dernieres_sorties':   dernieres_sorties,
        'graph_labels':        json.dumps(graph_labels),
        'graph_entrees':       json.dumps(graph_entrees),
        'graph_sorties':       json.dumps(graph_sorties),
        'nom_mois':            MOIS_FR[today.month],
        'annee':               today.year,
    })


def base(request):
    return render(request, 'base.html')


# ─────────────────────────────────────────────
#  PRODUITS — filtres avec infos de période
# ─────────────────────────────────────────────
def produit(request):
    search   = request.GET.get('q', '').strip()
    u        = request.user
    produits = Produit.objects.filter(utilisateur=u, supprime=False).order_by('-id')
    today    = timezone.now().date()

    # Récupérer les années disponibles pour le sélecteur
    annees_dispo = (
        Produit.objects.filter(supprime=False)
        .dates('date_ajout', 'year')
        .values_list('date_ajout__year', flat=True)
        .distinct()
        .order_by('-date_ajout__year')
    )
    annees_dispo = sorted(set(
        Produit.objects.filter(utilisateur=u, supprime=False)
        .values_list('date_ajout__year', flat=True)
        .distinct()
    ), reverse=True)

    filtre_annee = request.GET.get('annee', '')
    filtre_mois  = request.GET.get('mois', '')

    if filtre_annee:
        produits = produits.filter(date_ajout__year=int(filtre_annee))
    if filtre_mois:
        produits = produits.filter(date_ajout__month=int(filtre_mois))

    if search:
        produits = produits.filter(
            django_models.Q(nom__icontains=search) |
            django_models.Q(code_produit__icontains=search) |
            django_models.Q(famille__nom__icontains=search)
        )

    return render(request, 'produit.html', {
        'produits':      produits,
        'search':        search,
        'annees_dispo':  annees_dispo,
        'filtre_annee':  filtre_annee,
        'filtre_mois':   filtre_mois,
        'mois_fr':       MOIS_FR,
        'annee_courante': today.year,
    })


def ajouter_produit(request, type_produit):
    if type_produit not in ['alimentaire', 'non_alimentaire']:
        return redirect('produit')

    code_scan = request.GET.get('code', '')

    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, type_produit=type_produit)
        if form.is_valid():
            p = form.save(commit=False)
            p.type = type_produit
            p.utilisateur = request.user
            p.save()
            return redirect('produit')
    else:
        initial = {}
        if code_scan:
            initial['reference'] = code_scan
        form = ProduitForm(type_produit=type_produit, initial=initial)

    return render(request, 'ajouter_produit.html', {
        'form': form,
        'type_produit': type_produit,
        'est_alimentaire': type_produit == 'alimentaire',
        'code_scan': code_scan,
    })


def scanner_produit(request):
    return render(request, 'scanner_produit.html')


def lookup_barcode(request):
    code = request.GET.get('code', '').strip()
    if not code:
        return JsonResponse({'found': False})
    try:
        r = requests.get(
            f"https://world.openfoodfacts.org/api/v0/product/{code}.json",
            timeout=5
        )
        data = r.json()
        if data.get('status') == 1:
            p = data.get('product', {})
            return JsonResponse({
                'found': True,
                'nom':         p.get('product_name') or p.get('product_name_fr', ''),
                'marque':      p.get('brands', ''),
                'description': p.get('generic_name') or p.get('generic_name_fr', ''),
                'allergenes':  p.get('allergens_tags', []),
                'image':       p.get('image_front_url', ''),
            })
    except Exception:
        pass
    return JsonResponse({'found': False})


def supprimer_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk, utilisateur=request.user)
    if request.method == 'POST':
        produit.supprime = True
        produit.date_suppression = timezone.now()
        produit.save()
    return redirect('produit')


def corbeille_produits(request):
    produits = Produit.objects.filter(utilisateur=request.user, supprime=True).order_by('-date_suppression')
    return render(request, 'corbeille_produits.html', {'produits': produits})


def restaurer_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk, utilisateur=request.user, supprime=True)
    if request.method == 'POST':
        produit.supprime = False
        produit.date_suppression = None
        produit.save()
    return redirect('corbeille_produits')


def supprimer_definitif_produit(request, pk):
    produit = get_object_or_404(Produit, pk=pk, utilisateur=request.user, supprime=True)
    if request.method == 'POST':
        produit.delete()
    return redirect('corbeille_produits')


def familles_par_type(request):
    type_produit = request.GET.get('type')
    familles     = Famille.objects.filter(utilisateur=request.user, type=type_produit).values('id', 'nom')
    return JsonResponse(list(familles), safe=False)


def familles(request):
    liste = Famille.objects.filter(utilisateur=request.user).order_by('nom')
    form  = FamilleForm()
    if request.method == 'POST':
        form = FamilleForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.save(commit=False)
            f.utilisateur = request.user
            f.save()
            return redirect('familles')
    return render(request, 'familles.html', {'familles': liste, 'form': form})


def modifier_famille(request, pk):
    famille = get_object_or_404(Famille, pk=pk, utilisateur=request.user)
    if request.method == 'POST':
        form = FamilleForm(request.POST, request.FILES, instance=famille)
        if form.is_valid():
            form.save()
            return redirect('familles')
    else:
        form = FamilleForm(instance=famille)
    return render(request, 'modifier_famille.html', {'form': form, 'famille': famille})


def supprimer_famille(request, pk):
    famille = get_object_or_404(Famille, pk=pk, utilisateur=request.user)
    if request.method == 'POST':
        famille.delete()
        return redirect('familles')
    return render(request, 'confirmer_suppression_famille.html', {'famille': famille})


def entree_stock(request):
    entrees = EntreeStock.objects.filter(produit__utilisateur=request.user).select_related('produit', 'fournisseur').all()
    form    = EntreeStockForm(utilisateur=request.user)
    if request.method == 'POST':
        form = EntreeStockForm(request.POST, utilisateur=request.user)
        if form.is_valid():
            entree           = form.save()
            produit          = entree.produit
            produit.quantite += entree.quantite
            produit.save()
            return redirect('entree_stock')
    return render(request, 'entree_stock.html', {'entrees': entrees, 'form': form})


def supprimer_entree(request, pk):
    entree = get_object_or_404(EntreeStock, pk=pk, produit__utilisateur=request.user)
    if request.method == 'POST':
        produit          = entree.produit
        produit.quantite = max(0, produit.quantite - entree.quantite)
        produit.save()
        entree.delete()
        return redirect('entree_stock')
    return redirect('entree_stock')


def sortie_stock(request):
    sorties = SortieStock.objects.filter(produit__utilisateur=request.user).select_related('produit').all()
    form    = SortieStockForm(utilisateur=request.user)
    if request.method == 'POST':
        form = SortieStockForm(request.POST, utilisateur=request.user)
        if form.is_valid():
            sortie           = form.save()
            produit          = sortie.produit
            produit.quantite -= sortie.quantite
            produit.save()
            return redirect('sortie_stock')
    return render(request, 'sortie_stock.html', {'sorties': sorties, 'form': form})


def supprimer_sortie(request, pk):
    sortie = get_object_or_404(SortieStock, pk=pk, produit__utilisateur=request.user)
    if request.method == 'POST':
        produit          = sortie.produit
        produit.quantite += sortie.quantite
        produit.save()
        sortie.delete()
        return redirect('sortie_stock')
    return redirect('sortie_stock')


def fournisseurs(request):
    liste = Fournisseur.objects.filter(utilisateur=request.user).all()
    form  = FournisseurForm()
    if request.method == 'POST':
        form = FournisseurForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.utilisateur = request.user
            f.save()
            return redirect('fournisseurs')
    return render(request, 'fournisseurs.html', {'fournisseurs': liste, 'form': form})


def modifier_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk, utilisateur=request.user)
    if request.method == 'POST':
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            return redirect('fournisseurs')
    else:
        form = FournisseurForm(instance=fournisseur)
    return render(request, 'modifier_fournisseur.html', {'form': form, 'fournisseur': fournisseur})


def supprimer_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk, utilisateur=request.user)
    if request.method == 'POST':
        fournisseur.delete()
        return redirect('fournisseurs')
    return redirect('fournisseurs')


def detail_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk, utilisateur=request.user)
    entrees     = fournisseur.entreestock_set.select_related('produit').all()
    return render(request, 'detail_fournisseur.html', {'fournisseur': fournisseur, 'entrees': entrees})


@login_required
def parametres(request):
    user = request.user
    if request.method == 'POST':
        erreurs = []

        nouveau_username = request.POST.get('username', '').strip()
        nouvel_email     = request.POST.get('email', '').strip()
        if nouveau_username:
            user.username = nouveau_username
        if nouvel_email:
            user.email = nouvel_email

        if request.FILES.get('photo_profil'):
            user.photo_profil = request.FILES['photo_profil']

        # Infos entreprise
        user.nom_entreprise      = request.POST.get('nom_entreprise', '').strip()
        user.telephone_entreprise = request.POST.get('telephone_entreprise', '').strip()
        user.adresse_entreprise  = request.POST.get('adresse_entreprise', '').strip()

        ancien_mdp    = request.POST.get('ancien_mdp', '').strip()
        nouveau_mdp   = request.POST.get('nouveau_mdp', '').strip()
        confirmer_mdp = request.POST.get('confirmer_mdp', '').strip()

        if ancien_mdp or nouveau_mdp or confirmer_mdp:
            if not user.check_password(ancien_mdp):
                erreurs.append('Le mot de passe actuel est incorrect.')
            elif nouveau_mdp != confirmer_mdp:
                erreurs.append('Les nouveaux mots de passe ne correspondent pas.')
            elif len(nouveau_mdp) < 8:
                erreurs.append('Le nouveau mot de passe doit contenir au moins 8 caractères.')
            else:
                user.set_password(nouveau_mdp)
                update_session_auth_hash(request, user)

        if erreurs:
            for e in erreurs:
                messages.error(request, e)
        else:
            user.save()
            messages.success(request, 'Profil mis à jour avec succès !')

        return redirect('parametres')

    return render(request, 'parametres.html')

# ─────────────────────────────────────────────
#  Remplacez votre fonction accueil() dans views.py par celle-ci
# ─────────────────────────────────────────────

def accueil(request):
    today       = timezone.now().date()
    debut_mois  = today.replace(day=1)
    mois_dernier = (debut_mois - datetime.timedelta(days=1)).replace(day=1)

    # ── Cartes KPI ──────────────────────────────────────────
    total_produits      = Produit.objects.count()
    valeur_stock        = Produit.objects.aggregate(
                            v=Sum(F('quantite') * F('prix'))
                          )['v'] or 0

    # Produits sortis ce mois
    produits_sortis     = SortieStock.objects.filter(
                            date_sortie__gte=debut_mois
                          ).aggregate(total=Sum('quantite'))['total'] or 0

    # Alertes : produits dont la quantité est <= 10
    SEUIL_ALERTE = 10
    alertes_count = Produit.objects.filter(quantite__lte=SEUIL_ALERTE).count()

    # ── Tendances vs mois précédent ──────────────────────────
    produits_mois        = Produit.objects.filter(date_ajout__date__gte=debut_mois).count()
    produits_mois_dernier= Produit.objects.filter(
                             date_ajout__date__gte=mois_dernier,
                             date_ajout__date__lt=debut_mois
                           ).count()
    if produits_mois_dernier:
        trend_produits = round((produits_mois - produits_mois_dernier) / produits_mois_dernier * 100, 1)
    else:
        trend_produits = 0

    sortis_mois_dernier = SortieStock.objects.filter(
                            date_sortie__gte=mois_dernier,
                            date_sortie__lt=debut_mois
                          ).aggregate(total=Sum('quantite'))['total'] or 0
    if sortis_mois_dernier:
        trend_sortis = round((produits_sortis - sortis_mois_dernier) / sortis_mois_dernier * 100, 1)
    else:
        trend_sortis = 0

    # ── Tableau récapitulatif (10 derniers mouvements) ───────
    dernieres_entrees = EntreeStock.objects.select_related('produit', 'fournisseur').order_by('-date_entree')[:5]
    dernieres_sorties = SortieStock.objects.select_related('produit').order_by('-date_sortie')[:5]

    # ── Graphe : entrées et sorties par mois (6 derniers mois) ─
    six_mois_avant = today - datetime.timedelta(days=180)

    entrees_par_mois = (
        EntreeStock.objects
        .filter(date_entree__gte=six_mois_avant)
        .annotate(mois=TruncMonth('date_entree'))
        .values('mois')
        .annotate(total=Sum('quantite'))
        .order_by('mois')
    )

    sorties_par_mois = (
        SortieStock.objects
        .filter(date_sortie__gte=six_mois_avant)
        .annotate(mois=TruncMonth('date_sortie'))
        .values('mois')
        .annotate(total=Sum('quantite'))
        .order_by('mois')
    )

    # Construire les 6 derniers mois comme labels
    labels_mois = []
    for i in range(5, -1, -1):
        d = today - datetime.timedelta(days=30 * i)
        labels_mois.append(MOIS_FR[d.month][:3] + ' ' + str(d.year))

    def serie_par_mois(qs):
        data_map = {}
        for row in qs:
            key = MOIS_FR[row['mois'].month][:3] + ' ' + str(row['mois'].year)
            data_map[key] = row['total']
        return [data_map.get(l, 0) for l in labels_mois]

    graph_labels   = json.dumps(labels_mois)
    graph_entrees  = json.dumps(serie_par_mois(entrees_par_mois))
    graph_sorties  = json.dumps(serie_par_mois(sorties_par_mois))

    # ── Produits en alerte (pour le tableau alertes) ─────────
    produits_en_alerte = Produit.objects.filter(
        quantite__lte=SEUIL_ALERTE
    ).select_related('famille').order_by('quantite')[:20]

    return render(request, 'accueil.html', {
        # KPI
        'total_produits':   total_produits,
        'valeur_stock':     valeur_stock,
        'produits_sortis':  produits_sortis,
        'alertes_count':    alertes_count,
        'trend_produits':   trend_produits,
        'trend_sortis':     trend_sortis,
        'seuil_alerte':     SEUIL_ALERTE,
        # Tableaux
        'dernieres_entrees':   dernieres_entrees,
        'dernieres_sorties':   dernieres_sorties,
        'produits_en_alerte':  produits_en_alerte,
        # Graphe
        'graph_labels':   graph_labels,
        'graph_entrees':  graph_entrees,
        'graph_sorties':  graph_sorties,
        # Date
        'nom_mois':  MOIS_FR[today.month],
        'annee':     today.year,
    })


def statistiques(request):
    import calendar
    today = timezone.now().date()

    # ── Période sélectionnable ──
    annee_sel = int(request.GET.get('annee', today.year))
    mois_sel  = int(request.GET.get('mois', 0))  # 0 = toute l'année

    # ── KPI globaux ──
    total_produits   = Produit.objects.filter(utilisateur=request.user, supprime=False).count()
    valeur_stock     = Produit.objects.filter(utilisateur=request.user, supprime=False).aggregate(
        v=Sum(F('quantite') * F('prix'))
    )['v'] or 0
    produits_rupture = Produit.objects.filter(utilisateur=request.user, supprime=False, quantite=0).count()

    qs_entrees = EntreeStock.objects.filter(produit__utilisateur=request.user, date_entree__year=annee_sel)
    qs_sorties = SortieStock.objects.filter(produit__utilisateur=request.user, date_sortie__year=annee_sel)
    if mois_sel:
        qs_entrees = qs_entrees.filter(date_entree__month=mois_sel)
        qs_sorties = qs_sorties.filter(date_sortie__month=mois_sel)

    total_entrees_qte  = qs_entrees.aggregate(t=Sum('quantite'))['t'] or 0
    total_sorties_qte  = qs_sorties.aggregate(t=Sum('quantite'))['t'] or 0
    total_entrees_val  = qs_entrees.aggregate(t=Sum(F('quantite') * F('prix_achat')))['t'] or 0

    # ── Graphe mouvements mensuels (12 mois de l'année sélectionnée) ──
    graph_mois_labels  = [MOIS_FR[m][:3] for m in range(1, 13)]
    graph_mois_entrees = []
    graph_mois_sorties = []
    for m in range(1, 13):
        graph_mois_entrees.append(
            EntreeStock.objects.filter(produit__utilisateur=request.user, date_entree__year=annee_sel, date_entree__month=m)
            .aggregate(t=Sum('quantite'))['t'] or 0
        )
        graph_mois_sorties.append(
            SortieStock.objects.filter(produit__utilisateur=request.user, date_sortie__year=annee_sel, date_sortie__month=m)
            .aggregate(t=Sum('quantite'))['t'] or 0
        )

    # ── Top 5 produits les plus sortis ──
    top_sorties = (
        SortieStock.objects.filter(produit__utilisateur=request.user, date_sortie__year=annee_sel)
        .values('produit__nom')
        .annotate(total=Sum('quantite'))
        .order_by('-total')[:5]
    )

    # ── Top 5 produits les plus entrés ──
    top_entrees = (
        EntreeStock.objects.filter(produit__utilisateur=request.user, date_entree__year=annee_sel)
        .values('produit__nom')
        .annotate(total=Sum('quantite'))
        .order_by('-total')[:5]
    )

    # ── Répartition par motif de sortie ──
    motifs = (
        SortieStock.objects.filter(produit__utilisateur=request.user, date_sortie__year=annee_sel)
        .values('motif')
        .annotate(total=Sum('quantite'))
        .order_by('-total')
    )
    MOTIF_LABELS = {
        'vente': 'Vente', 'consommation': 'Consommation',
        'perte': 'Perte/Périmé', 'retour': 'Retour', 'autre': 'Autre'
    }
    motifs_labels = json.dumps([MOTIF_LABELS.get(m['motif'], m['motif']) for m in motifs])
    motifs_data   = json.dumps([m['total'] for m in motifs])

    # ── Répartition stock par famille ──
    familles_stock = (
        Produit.objects.filter(utilisateur=request.user, supprime=False)
        .values('famille__nom')
        .annotate(total=Sum('quantite'))
        .order_by('-total')[:8]
    )
    familles_labels = json.dumps([f['famille__nom'] or 'Sans famille' for f in familles_stock])
    familles_data   = json.dumps([f['total'] for f in familles_stock])

    # ── Bilan financier mensuel ──
    bilan_labels  = [MOIS_FR[m][:3] for m in range(1, 13)]
    bilan_achats  = []
    for m in range(1, 13):
        bilan_achats.append(
            float(EntreeStock.objects.filter(date_entree__year=annee_sel, date_entree__month=m)
            .aggregate(t=Sum(F('quantite') * F('prix_achat')))['t'] or 0)
        )

    # ── Années disponibles ──
    annees = sorted(set(
        list(EntreeStock.objects.filter(produit__utilisateur=request.user).values_list('date_entree__year', flat=True).distinct()) +
        list(SortieStock.objects.filter(produit__utilisateur=request.user).values_list('date_sortie__year', flat=True).distinct())
    ), reverse=True) or [today.year]

    return render(request, 'statistiques.html', {
        'total_produits':      total_produits,
        'valeur_stock':        valeur_stock,
        'produits_rupture':    produits_rupture,
        'total_entrees_qte':   total_entrees_qte,
        'total_sorties_qte':   total_sorties_qte,
        'total_entrees_val':   total_entrees_val,
        'top_sorties':         top_sorties,
        'top_entrees':         top_entrees,
        'graph_mois_labels':   json.dumps(graph_mois_labels),
        'graph_mois_entrees':  json.dumps(graph_mois_entrees),
        'graph_mois_sorties':  json.dumps(graph_mois_sorties),
        'motifs_labels':       motifs_labels,
        'motifs_data':         motifs_data,
        'familles_labels':     familles_labels,
        'familles_data':       familles_data,
        'bilan_labels':        json.dumps(bilan_labels),
        'bilan_achats':        json.dumps(bilan_achats),
        'annees':              annees,
        'annee_sel':           annee_sel,
        'mois_sel':            mois_sel,
        'mois_fr':             MOIS_FR,
        'nom_mois':            MOIS_FR[today.month],
        'annee':               today.year,
    })
