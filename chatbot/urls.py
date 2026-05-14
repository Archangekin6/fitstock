from django.urls import path
from .views import chatbot_ai_action

urlpatterns = [
    path("ai/", chatbot_ai_action, name="chatbot_ai_action"),
]