#!/usr/bin/env python
"""
Script para probar los endpoints de administración
"""
import os
import sys
import django

# Agregar el directorio raíz del proyecto al PYTHONPATH
# Esto permite que Django encuentre el módulo 'delivery_api'
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'delivery_api.settings')

# Inicializar Django
django.setup()

# Ahora importar los modelos
from django.contrib.auth import get_user_model
from django.test.client import Client
import json

User = get_user_model()

def test_admin_endpoints():
    print("=" * 60)
    print("🧪 PROBANDO ENDPOINTS DE ADMINISTRACIÓN")
    print("=" * 60)
    
    # 1. Crear usuario admin si no existe
    admin, created = User.objects.get_or_create(
        username='admin_test',
        defaults={
            'email': 'admin@test.com',
            'first_name': 'Admin',
            'last_name': 'Test',
            'user_type': 'admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('Admin123!')
        admin.save()
        print("✅ Admin creado")
    else:
        print("ℹ️ Admin ya existe")
    
    # 2. Crear usuarios de prueba
    test_users = [
        {'username': 'cliente1', 'user_type': 'client', 'email': 'cliente1@test.com'},
        {'username': 'repartidor1', 'user_type': 'delivery', 'email': 'repartidor1@test.com'},
        {'username': 'restaurante1', 'user_type': 'restaurant', 'email': 'restaurante1@test.com'},
    ]
    
    for user_data in test_users:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'user_type': user_data['user_type'],
                'is_active': True
            }
        )
        if created:
            user.set_password('Test123!')
            user.save()
            print(f"✅ Usuario creado: {user_data['username']}")
        else:
            print(f"ℹ️ Usuario ya existe: {user_data['username']}")
    
    print("\n" + "=" * 60)
    print("📊 ENDPOINTS DISPONIBLES:")
    print("=" * 60)
    
    endpoints = [
        ("GET", "/api/v1/users/admin/stats/", "Estadísticas de usuarios"),
        ("GET", "/api/v1/users/admin/users/", "Listar todos los usuarios"),
        ("GET", "/api/v1/users/admin/users/filter/?user_type=client", "Filtrar por tipo"),
        ("GET", "/api/v1/users/admin/users/filter/?is_active=true", "Filtrar por estado"),
        ("GET", "/api/v1/users/admin/users/1/", "Detalle de usuario"),
        ("POST", "/api/v1/users/admin/users/2/toggle-active/", "Activar/Desactivar usuario"),
        ("POST", "/api/v1/users/admin/users/3/toggle-verify/", "Verificar/Desverificar restaurante"),
    ]
    
    for method, url, desc in endpoints:
        print(f"  {method} {url}")
        print(f"    └─ {desc}")
    
    print("\n" + "=" * 60)
    print("🚀 Para probar con curl:")
    print("=" * 60)
    
    # Obtener el dominio según el entorno
    if os.getenv('DEBUG', 'True') == 'True':
        base_url = "http://localhost:8000"
    else:
        base_url = "https://sabi-x-delivery.duckdns.org"
    
    print(f"\n# 1. Obtener token de admin")
    print(f"curl -X POST {base_url}/api/v1/users/login/ \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"username\":\"admin_test\",\"password\":\"Admin123!\"}'")
    
    print(f"\n# 2. Listar usuarios (usar el token obtenido)")
    print(f"curl -X GET {base_url}/api/v1/users/admin/users/ \\")
    print("  -H 'Authorization: Bearer TU_ACCESS_TOKEN'")
    
    print(f"\n# 3. Estadísticas del dashboard")
    print(f"curl -X GET {base_url}/api/v1/users/admin/stats/ \\")
    print("  -H 'Authorization: Bearer TU_ACCESS_TOKEN'")
    
    print("\n" + "=" * 60)
    print("✅ Script ejecutado correctamente")
    print("=" * 60)

if __name__ == "__main__":
    test_admin_endpoints()