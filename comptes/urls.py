from django.urls import path
from . import views

urlpatterns = [
    # authentification
    path('inscription/',    views.inscription,    name='inscription'),
    path('',                views.connexion,      name='connexion'),
    path('deconnexion/',    views.deconnexion,    name='deconnexion'),
    path('verifier-email/', views.verifier_email, name='verifier_email'),
    path('renvoyer-code/',  views.renvoyer_code,  name='renvoyer_code'),
    # dashboard
    path('accueil/', views.accueil, name='accueil'),
    path('base/',    views.base,    name='base'),
    # produits
    path('produit/',                                    views.produit,                   name='produit'),
    path('produit/scanner/',                            views.scanner_produit,           name='scanner_produit'),
    path('produit/lookup-barcode/',                     views.lookup_barcode,            name='lookup_barcode'),
    path('produit/ajouter/<str:type_produit>/',         views.ajouter_produit,           name='ajouter_produit'),
    path('produit/supprimer/<int:pk>/',                 views.supprimer_produit,         name='supprimer_produit'),
    path('produit/corbeille/',                          views.corbeille_produits,        name='corbeille_produits'),
    path('produit/restaurer/<int:pk>/',                 views.restaurer_produit,         name='restaurer_produit'),
    path('produit/supprimer-definitif/<int:pk>/',       views.supprimer_definitif_produit, name='supprimer_definitif_produit'),
    # familles
    path('familles/',                       views.familles,         name='familles'),
    path('familles/modifier/<int:pk>/',     views.modifier_famille, name='modifier_famille'),
    path('familles/supprimer/<int:pk>/',    views.supprimer_famille, name='supprimer_famille'),
    # entrées de stock
    path('entree-stock/',                       views.entree_stock,    name='entree_stock'),
    path('entree-stock/supprimer/<int:pk>/',    views.supprimer_entree, name='supprimer_entree'),
    # sorties de stock
    path('sortie-stock/',                       views.sortie_stock,    name='sortie_stock'),
    path('sortie-stock/supprimer/<int:pk>/',    views.supprimer_sortie, name='supprimer_sortie'),
    # fournisseurs
    path('fournisseurs/',                       views.fournisseurs,          name='fournisseurs'),
    path('fournisseurs/modifier/<int:pk>/',     views.modifier_fournisseur,  name='modifier_fournisseur'),
    path('fournisseurs/supprimer/<int:pk>/',    views.supprimer_fournisseur, name='supprimer_fournisseur'),
    path('fournisseurs/<int:pk>/',              views.detail_fournisseur,    name='detail_fournisseur'),
    # autres
    path('parametres/',   views.parametres,   name='parametres'),
    path('statistiques/', views.statistiques, name='statistiques'),
]
