"""
Configuración de Firebase para el backend de Delivery Platform
"""

import os
from pathlib import Path
import json
from django.conf import settings

# Ruta del archivo de credenciales
FIREBASE_CREDENTIALS_FILE = os.path.join(
    settings.BASE_DIR, 
    'firebase', 
    'sabixdelivery-firebase-adminsdk-fbsvc-3572815d44.json'
)

# Inicializar Firebase solo si el archivo existe
def init_firebase():
    """
    Inicializa Firebase con las credenciales del archivo
    """
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        
        if os.path.exists(FIREBASE_CREDENTIALS_FILE):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
            firebase_app = firebase_admin.initialize_app(cred)
            print("✅ Firebase inicializado correctamente")
            return True
        else:
            print(f"⚠️ Archivo de credenciales no encontrado: {FIREBASE_CREDENTIALS_FILE}")
            return False
    except Exception as e:
        print(f"❌ Error inicializando Firebase: {e}")
        return False

# Variable para verificar si Firebase está disponible
FIREBASE_AVAILABLE = init_firebase()