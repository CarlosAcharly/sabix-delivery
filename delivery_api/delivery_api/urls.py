# delivery_api/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # Incluir las URLs de users
    path('api/v1/users/', include('users.urls')),  
    path('api/v1/auth/', include('users.urls')),   
    path('api/v1/products/', include('products.urls')), 
    
     # =============================================
    # ORDERS API - NUEVO
    # =============================================
    path('api/v1/orders/', include('orders.urls')),
]

# Solo para desarrollo - servir archivos estáticos y media
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)