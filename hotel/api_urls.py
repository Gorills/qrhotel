from django.urls import path
from . import api_views

urlpatterns = [
    path('telegram/webhook/', api_views.telegram_webhook, name='telegram_webhook'),
    path('orders/live/', api_views.orders_live, name='orders_live'),
    path('notifications/unviewed/', api_views.unviewed_orders, name='unviewed_orders'),
    path('orders/<int:order_id>/mark-viewed/', api_views.mark_order_viewed, name='mark_order_viewed'),
]

