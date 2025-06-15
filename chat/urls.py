from django.urls import path

from chat.views import ws_chat_view, metrics_view

urlpatterns = [
    path('ws/', ws_chat_view, name='ws_chat_view'),
    path('metrics/', metrics_view, name='metrics'),
]