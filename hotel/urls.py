from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('building/<slug:building_slug>/', views.building_page, name='building_page'),
    path('building/<slug:building_slug>/cart/', views.building_get_cart, name='building_get_cart'),
    path('building/<slug:building_slug>/cart/add/', views.building_cart_add, name='building_cart_add'),
    path('building/<slug:building_slug>/cart/remove/', views.building_cart_remove, name='building_cart_remove'),
    path('building/<slug:building_slug>/cart/update/', views.building_cart_update, name='building_cart_update'),
    path('building/<slug:building_slug>/create/', views.building_create_order, name='building_create_order'),
    path('building/<slug:building_slug>/status/<int:order_id>/', views.building_order_status, name='building_order_status'),
    path('floor/<slug:floor_slug>/', views.floor_page, name='floor_page'),
    path('floor/<slug:floor_slug>/cart/', views.floor_get_cart, name='floor_get_cart'),
    path('floor/<slug:floor_slug>/cart/add/', views.floor_cart_add, name='floor_cart_add'),
    path('floor/<slug:floor_slug>/cart/remove/', views.floor_cart_remove, name='floor_cart_remove'),
    path('floor/<slug:floor_slug>/cart/update/', views.floor_cart_update, name='floor_cart_update'),
    path('floor/<slug:floor_slug>/create/', views.floor_create_order, name='floor_create_order'),
    path('floor/<slug:floor_slug>/status/<int:order_id>/', views.floor_order_status, name='floor_order_status'),
    path('order/<slug:room_slug>/', views.order_page, name='order_page'),
    path('order/<slug:room_slug>/cart/', views.get_cart, name='get_cart'),
    path('order/<slug:room_slug>/cart/add/', views.cart_add, name='cart_add'),
    path('order/<slug:room_slug>/cart/remove/', views.cart_remove, name='cart_remove'),
    path('order/<slug:room_slug>/cart/update/', views.cart_update, name='cart_update'),
    path('order/<slug:room_slug>/create/', views.create_order, name='create_order'),
    path('order/<slug:room_slug>/status/<int:order_id>/', views.order_status, name='order_status'),
]

