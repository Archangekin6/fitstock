from django.shortcuts import render

import json
import requests
from datetime import date, timedelta

from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from comptes.models import Produit, EntreeStock, SortieStock


HF_MODEL_URL = "https://router.huggingface.co/v1/chat/completions"


def ask_huggingface(prompt):
    headers = {
        "Authorization": f"Bearer {settings.HF_API_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "Qwen/Qwen2.5-72B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 200,
        "temperature": 0.2,
    }

    r = requests.post(HF_MODEL_URL, headers=headers, json=payload)
    if r.status_code != 200:
        return None, f"Erreur HuggingFace {r.status_code}: {r.text}"

    data = r.json()
    try:
        return data["choices"][0]["message"]["content"], None
    except (KeyError, IndexError):
        return None, "Réponse invalide de HuggingFace"


def find_product_by_name(name):
    if not name:
        return None

    produit = Produit.objects.filter(nom__icontains=name).first()
    return produit


@csrf_exempt
def chatbot_ai_action(request):
    message = request.GET.get("message", "").strip()

    if not message:
        return JsonResponse({"response": "Écris un message 😊"})

    # PROMPT pour forcer l'IA à répondre en JSON
    prompt = f"""
Tu es un assistant de gestion de stock.
Tu dois analyser le message utilisateur et répondre uniquement en JSON valide.
Aucune phrase, aucun commentaire, uniquement un JSON.

Actions possibles :
- stock_product (voir stock d'un produit)
- list_products (liste des produits)
- rupture (produits en rupture)
- expiring (produits bientôt périmés)
- add_stock (ajouter quantité)
- remove_stock (retirer quantité)

Format obligatoire :
{{
  "action": "...",
  "product": "...",
  "quantity": 0
}}

Règles :
- product doit être le nom du produit si possible sinon null
- quantity doit être un nombre sinon 0

Message utilisateur : "{message}"
"""

    ai_text, error = ask_huggingface(prompt)

    if error:
        return JsonResponse({"response": "⚠️ Problème IA : " + error})

    # Nettoyage si l'IA renvoie du texte avant/après le JSON
    try:
        start = ai_text.find("{")
        end = ai_text.rfind("}") + 1
        ai_json = ai_text[start:end]
        data = json.loads(ai_json)
    except:
        return JsonResponse({"response": "⚠️ Je n'ai pas compris ta demande. Réessaie autrement."})

    action = data.get("action")
    product_name = data.get("product")
    quantity = data.get("quantity", 0)

    produit = find_product_by_name(product_name)

    # -----------------------------
    # ACTION : LISTE PRODUITS
    # -----------------------------
    if action == "list_products":
        produits = Produit.objects.all().order_by("nom")
        if produits.exists():
            txt = "📋 Liste des produits :\n"
            txt += "\n".join([f"- {p.nom} (Stock: {p.quantite})" for p in produits[:30]])
            return JsonResponse({"response": txt})
        return JsonResponse({"response": "Aucun produit enregistré."})

    # -----------------------------
    # ACTION : PRODUITS EN RUPTURE
    # -----------------------------
    if action == "rupture":
        produits = Produit.objects.filter(quantite=0)
        if produits.exists():
            txt = "🚨 Produits en rupture :\n"
            txt += "\n".join([f"- {p.nom}" for p in produits])
            return JsonResponse({"response": txt})
        return JsonResponse({"response": "✅ Aucun produit en rupture."})

    # -----------------------------
    # ACTION : PRODUITS BIENTÔT PÉRIMÉS
    # -----------------------------
    if action == "expiring":
        limite = date.today() + timedelta(days=7)
        produits = Produit.objects.filter(date_expiration__isnull=False, date_expiration__lte=limite)

        if produits.exists():
            txt = "⏳ Produits bientôt périmés (7 jours) :\n"
            txt += "\n".join([f"- {p.nom} (Expire le {p.date_expiration})" for p in produits])
            return JsonResponse({"response": txt})
        return JsonResponse({"response": "✅ Aucun produit bientôt périmé."})

    # -----------------------------
    # ACTION : STOCK D'UN PRODUIT
    # -----------------------------
    if action == "stock_product":
        if not produit:
            return JsonResponse({"response": "Je ne trouve pas ce produit. Donne-moi le nom exact."})

        return JsonResponse({"response": f"📦 Stock actuel de {produit.nom} : {produit.quantite} unités."})

    # -----------------------------
    # ACTION : AJOUTER STOCK
    # -----------------------------
    if action == "add_stock":
        if not produit:
            return JsonResponse({"response": "Je ne trouve pas le produit. Exemple : ajoute 10 riz."})

        if quantity <= 0:
            return JsonResponse({"response": "Donne une quantité valide. Exemple : ajoute 10 riz."})

        produit.quantite += int(quantity)
        produit.save()

        # Enregistrer l'entrée stock
        EntreeStock.objects.create(
            produit=produit,
            quantite=int(quantity),
            prix_achat=0,
            date_entree=date.today(),
            note="Ajout via chatbot IA"
        )

        return JsonResponse({"response": f"✅ Stock mis à jour : {produit.nom} = {produit.quantite} unités."})

    # -----------------------------
    # ACTION : RETIRER STOCK
    # -----------------------------
    if action == "remove_stock":
        if not produit:
            return JsonResponse({"response": "Je ne trouve pas le produit. Exemple : retire 5 sucre."})

        if quantity <= 0:
            return JsonResponse({"response": "Donne une quantité valide. Exemple : retire 5 sucre."})

        if produit.quantite < int(quantity):
            return JsonResponse({"response": f"⚠️ Stock insuffisant. {produit.nom} = {produit.quantite} unités."})

        produit.quantite -= int(quantity)
        produit.save()

        SortieStock.objects.create(
            produit=produit,
            quantite=int(quantity),
            motif="vente",
            date_sortie=date.today(),
            note="Sortie via chatbot IA"
        )

        return JsonResponse({"response": f"✅ Stock mis à jour : {produit.nom} = {produit.quantite} unités."})

    return JsonResponse({"response": "Je ne comprends pas cette demande."})
# Create your views here.
