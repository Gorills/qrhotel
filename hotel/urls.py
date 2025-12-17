from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('order/<slug:room_slug>/', views.order_page, name='order_page'),
    path('order/<slug:room_slug>/cart/', views.get_cart, name='get_cart'),
    path('order/<slug:room_slug>/cart/add/', views.cart_add, name='cart_add'),
    path('order/<slug:room_slug>/cart/remove/', views.cart_remove, name='cart_remove'),
    path('order/<slug:room_slug>/cart/update/', views.cart_update, name='cart_update'),
    path('order/<slug:room_slug>/create/', views.create_order, name='create_order'),
    path('order/<slug:room_slug>/status/<int:order_id>/', views.order_status, name='order_status'),
]

