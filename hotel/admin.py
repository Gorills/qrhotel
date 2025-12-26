from django.contrib import admin
from .models import Building, Floor, Room, Category, Product, Order, OrderItem


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'slug']
    search_fields = ['name', 'slug']
    readonly_fields = ['token', 'qr_code']
    list_editable = ['is_active']


@admin.register(Floor)
class FloorAdmin(admin.ModelAdmin):
    list_display = ['name', 'building', 'number', 'is_active', 'slug']
    list_filter = ['building', 'is_active']
    search_fields = ['name', 'number', 'slug']
    readonly_fields = ['token', 'qr_code']
    list_editable = ['is_active']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['number', 'floor', 'is_active', 'slug']
    list_filter = ['floor__building', 'floor', 'is_active']
    search_fields = ['number', 'slug']
    readonly_fields = ['token', 'qr_code']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order_priority', 'is_active']
    list_editable = ['order_priority', 'is_active']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available', 'order_priority']
    list_filter = ['category', 'is_available']
    list_editable = ['is_available', 'order_priority']
    search_fields = ['name', 'description']
    raw_id_fields = ['category']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['price_at_moment']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'room', 'building', 'floor', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'created_at', 'is_archived']
    search_fields = ['room__number', 'building__name', 'floor__name', 'session_key']
    readonly_fields = ['created_at', 'updated_at', 'session_key']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'




