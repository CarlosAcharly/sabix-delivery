from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'get_full_name', 'is_active', 'created_at')
    list_filter = ('user_type', 'is_active', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone')
    ordering = ('-created_at',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Información Personal', {
            'fields': ('phone', 'profile_image', 'user_type')
        }),
        ('Información de Cliente', {
            'fields': ('address', 'preferred_payment_method'),
            'classes': ('collapse',)
        }),
        ('Información de Repartidor', {
            'fields': ('vehicle_type', 'vehicle_plate', 'is_available', 
                      'current_location_lat', 'current_location_lng'),
            'classes': ('collapse',)
        }),
        ('Información de Restaurante', {
            'fields': ('restaurant_name', 'restaurant_description', 'restaurant_address',
                      'restaurant_phone', 'is_restaurant_verified', 'parent_restaurant'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('user_type', 'phone', 'address', 'vehicle_type', 
                      'vehicle_plate', 'restaurant_name', 'restaurant_address')
        }),
    )

admin.site.register(User, CustomUserAdmin)