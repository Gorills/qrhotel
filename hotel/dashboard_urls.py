from django.urls import path
from . import views
from .qr_generator import generate_qr_images

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('rooms/', views.dashboard_rooms, name='dashboard_rooms'),
    path('menu/', views.dashboard_menu, name='dashboard_menu'),
    path('statistics/', views.dashboard_statistics, name='dashboard_statistics'),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('products/<int:product_id>/toggle/', views.toggle_product_availability, name='toggle_product_availability'),
    path('qr/generate/', generate_qr_images, name='generate_qr_images'),
    # Management URLs
    path('building/add/', views.dashboard_building_add, name='dashboard_building_add'),
    path('building/<int:building_id>/delete/', views.dashboard_building_delete, name='dashboard_building_delete'),
    path('floor/add/', views.dashboard_floor_add, name='dashboard_floor_add'),
    path('floor/<int:floor_id>/delete/', views.dashboard_floor_delete, name='dashboard_floor_delete'),
    path('room/add/', views.dashboard_room_add, name='dashboard_room_add'),
    path('room/<int:room_id>/delete/', views.dashboard_room_delete, name='dashboard_room_delete'),
    path('room/<int:room_id>/regenerate-qr/', views.dashboard_room_regenerate_qr, name='dashboard_room_regenerate_qr'),
    path('category/add/', views.dashboard_category_add, name='dashboard_category_add'),
    path('category/<int:category_id>/edit/', views.dashboard_category_edit, name='dashboard_category_edit'),
    path('category/<int:category_id>/delete/', views.dashboard_category_delete, name='dashboard_category_delete'),
    path('product/add/', views.dashboard_product_add, name='dashboard_product_add'),
    path('product/<int:product_id>/edit/', views.dashboard_product_edit, name='dashboard_product_edit'),
    path('product/<int:product_id>/delete/', views.dashboard_product_delete, name='dashboard_product_delete'),
    path('settings/', views.dashboard_settings, name='dashboard_settings'),
]

