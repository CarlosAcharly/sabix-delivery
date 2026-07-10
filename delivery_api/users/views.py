from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from rest_framework.permissions import AllowAny
from django.db.models import Count, Q
from .models import User
from .serializers import (
    # Serializers existentes
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    UserProfileUpdateSerializer,
    PasswordChangeSerializer,
    UserTokenRefreshSerializer,
    
    # Serializers de Administración
    AdminUserListSerializer,
    AdminUserDetailSerializer,
    AdminUserUpdateSerializer,
    AdminUserStatsSerializer,
)

# =============================================
# REGISTRO DE USUARIOS
# =============================================

class RegisterView(generics.CreateAPIView):
    """
    Vista para registrar nuevos usuarios
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generar tokens JWT
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)

# =============================================
# LOGIN GENÉRICO (Con verificación de app_type)
# =============================================

class LoginView(APIView):
    """
    Vista para iniciar sesión con verificación de tipo de usuario
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Obtener el tipo de app del body o del header
        app_type = request.data.get('app_type') or request.headers.get('X-App-Type', 'client')
        
        # Validar que app_type sea válido
        valid_app_types = ['client', 'delivery', 'restaurant', 'admin_web', 'restaurant_web']
        if app_type not in valid_app_types:
            return Response(
                {'error': f'Tipo de aplicación inválido. Opciones: {", ".join(valid_app_types)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear una copia de los datos para poder modificarlos
        data = request.data.copy()
        data['app_type'] = app_type
        
        serializer = UserLoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

# =============================================
# LOGIN ESPECÍFICOS POR APP (VERSIÓN CORREGIDA)
# =============================================

class ClientLoginView(APIView):
    """
    Login exclusivo para la app de Cliente
    Solo usuarios con user_type='client' pueden acceder
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Crear una copia de los datos para poder modificarlos
        data = request.data.copy()
        data['app_type'] = 'client'
        
        serializer = UserLoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class DeliveryLoginView(APIView):
    """
    Login exclusivo para la app de Repartidor
    Solo usuarios con user_type='delivery' pueden acceder
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        data = request.data.copy()
        data['app_type'] = 'delivery'
        
        serializer = UserLoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class RestaurantLoginView(APIView):
    """
    Login exclusivo para la app de Restaurante
    Usuarios con user_type='restaurant' o 'admin' pueden acceder
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        data = request.data.copy()
        data['app_type'] = 'restaurant'
        
        serializer = UserLoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

class AdminWebLoginView(APIView):
    """
    Login exclusivo para el Panel de Administración Web
    Solo usuarios con user_type='admin' pueden acceder
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        try:
            # Crear una copia de los datos para poder modificarlos
            data = request.data.copy()
            data['app_type'] = 'admin_web'
            
            serializer = UserLoginSerializer(data=data)
            
            if serializer.is_valid():
                return Response(serializer.validated_data, status=status.HTTP_200_OK)
            
            # Si hay errores de validación, devolverlos
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Capturar cualquier error y devolverlo
            import traceback
            print(f"Error en AdminWebLoginView: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': f'Error interno del servidor: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class RestaurantWebLoginView(APIView):
    """
    Login exclusivo para el Panel Web de Restaurante
    Usuarios con user_type='restaurant' o 'admin' pueden acceder
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        data = request.data.copy()
        data['app_type'] = 'restaurant_web'
        
        serializer = UserLoginSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

# =============================================
# PERFIL DE USUARIO
# =============================================

class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Vista para obtener y actualizar el perfil del usuario
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return UserSerializer
        return UserProfileUpdateSerializer
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = UserSerializer(instance)
        return Response(serializer.data)

# =============================================
# LOGOUT
# =============================================

class LogoutView(APIView):
    """
    Vista para cerrar sesión (invalida el token refresh)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Sesión cerrada exitosamente'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# =============================================
# CAMBIO DE CONTRASEÑA
# =============================================

class PasswordChangeView(APIView):
    """
    Vista para cambiar contraseña
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Contraseña actualizada exitosamente'}, status=status.HTTP_200_OK)

# =============================================
# VALIDACIONES
# =============================================

class CheckUsernameView(APIView):
    """
    Vista para verificar si un username está disponible
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        username = request.query_params.get('username')
        if not username:
            return Response({'error': 'Username requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = User.objects.filter(username=username).exists()
        return Response({'username': username, 'available': not exists})

class CheckEmailView(APIView):
    """
    Vista para verificar si un email está disponible
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        email = request.query_params.get('email')
        if not email:
            return Response({'error': 'Email requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = User.objects.filter(email=email).exists()
        return Response({'email': email, 'available': not exists})

# =============================================
# REFRESH TOKEN
# =============================================

class CustomTokenRefreshView(TokenRefreshView):
    """
    Vista personalizada para refrescar token JWT
    """
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

# =============================================
# RAÍZ DE LA API
# =============================================

class APIRootView(APIView):
    """
    Vista raíz de la API de usuarios
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'success',
            'message': 'Bienvenido a la API de Delivery Platform',
            'endpoints': {
                'registro': '/api/v1/users/register/',
                'login': '/api/v1/users/login/',
                'login_client': '/api/v1/users/login/client/',
                'login_delivery': '/api/v1/users/login/delivery/',
                'login_restaurant': '/api/v1/users/login/restaurant/',
                'login_admin': '/api/v1/users/login/admin/',
                'login_restaurant_web': '/api/v1/users/login/restaurant-web/',
                'logout': '/api/v1/users/logout/',
                'perfil': '/api/v1/users/profile/',
                'cambiar_contraseña': '/api/v1/users/change-password/',
                'refrescar_token': '/api/v1/users/token/refresh/',
                'verificar_username': '/api/v1/users/check-username/?username=valor',
                'verificar_email': '/api/v1/users/check-email/?email=valor',
                'admin_usuarios': '/api/v1/users/admin/users/',
                'admin_stats': '/api/v1/users/admin/stats/',
            },
            'documentacion': 'Próximamente...'
        })

# =============================================
# ADMINISTRACIÓN DE USUARIOS
# =============================================

from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend

class AdminUserListView(generics.ListAPIView):
    """
    Vista para listar todos los usuarios (solo admin)
    """
    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone']
    ordering_fields = ['id', 'username', 'email', 'user_type', 'created_at', 'is_active']
    filterset_fields = ['user_type', 'is_active', 'is_restaurant_verified']
    
    def get_queryset(self):
        # Solo admins pueden ver todos los usuarios
        if not self.request.user.is_admin_user:
            return User.objects.none()
        return User.objects.all().order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar o eliminar un usuario específico (solo admin)
    """
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'
    
    def get_queryset(self):
        if not self.request.user.is_admin_user:
            return User.objects.none()
        return User.objects.all()
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return AdminUserDetailSerializer
        return AdminUserUpdateSerializer
    
    def destroy(self, request, *args, **kwargs):
        # No permitir eliminar al propio admin
        instance = self.get_object()
        if instance.id == request.user.id:
            return Response(
                {'error': 'No puedes eliminar tu propio usuario'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

class AdminUserToggleActiveView(APIView):
    """
    Vista para activar/desactivar un usuario
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        if not request.user.is_admin_user:
            return Response(
                {'error': 'No tienes permisos para realizar esta acción'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # No permitir desactivar al propio admin
        if user.id == request.user.id:
            return Response(
                {'error': 'No puedes desactivar tu propio usuario'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.is_active = not user.is_active
        user.save()
        
        return Response({
            'message': f'Usuario {"activado" if user.is_active else "desactivado"} exitosamente',
            'is_active': user.is_active
        })

class AdminUserToggleVerifyView(APIView):
    """
    Vista para verificar/desverificar un restaurante
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        if not request.user.is_admin_user:
            return Response(
                {'error': 'No tienes permisos para realizar esta acción'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            user = User.objects.get(id=user_id, user_type='restaurant')
        except User.DoesNotExist:
            return Response(
                {'error': 'Restaurante no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        user.is_restaurant_verified = not user.is_restaurant_verified
        user.save()
        
        return Response({
            'message': f'Restaurante {"verificado" if user.is_restaurant_verified else "desverificado"} exitosamente',
            'is_restaurant_verified': user.is_restaurant_verified
        })

class AdminUserStatsView(APIView):
    """
    Vista para obtener estadísticas de usuarios (para el dashboard)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_admin_user:
            return Response(
                {'error': 'No tienes permisos para realizar esta acción'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Estadísticas básicas
        total_users = User.objects.count()
        total_clients = User.objects.filter(user_type='client').count()
        total_deliveries = User.objects.filter(user_type='delivery').count()
        total_restaurants = User.objects.filter(user_type='restaurant').count()
        total_admins = User.objects.filter(user_type='admin').count()
        
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = User.objects.filter(is_active=False).count()
        
        verified_restaurants = User.objects.filter(
            user_type='restaurant', 
            is_restaurant_verified=True
        ).count()
        
        unverified_restaurants = User.objects.filter(
            user_type='restaurant', 
            is_restaurant_verified=False
        ).count()
        
        available_deliveries = User.objects.filter(
            user_type='delivery', 
            is_available=True,
            is_active=True
        ).count()
        
        unavailable_deliveries = User.objects.filter(
            user_type='delivery', 
            is_available=False,
            is_active=True
        ).count()
        
        # Usuarios recientes (últimos 10)
        recent_users = User.objects.all().order_by('-created_at')[:10]
        recent_users_data = AdminUserListSerializer(recent_users, many=True).data
        
        # Usuarios por día (últimos 7 días)
        from django.utils import timezone
        from datetime import timedelta
        
        seven_days_ago = timezone.now() - timedelta(days=7)
        users_by_day = User.objects.filter(
            created_at__gte=seven_days_ago
        ).extra(
            {'day': "date(created_at)"}
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        stats = {
            'total_users': total_users,
            'total_clients': total_clients,
            'total_deliveries': total_deliveries,
            'total_restaurants': total_restaurants,
            'total_admins': total_admins,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'verified_restaurants': verified_restaurants,
            'unverified_restaurants': unverified_restaurants,
            'available_deliveries': available_deliveries,
            'unavailable_deliveries': unavailable_deliveries,
            'recent_users': recent_users_data,
            'users_by_day': list(users_by_day)
        }
        
        return Response(stats)

class AdminUserFilterView(generics.ListAPIView):
    """
    Vista para filtrar usuarios por tipo y estado
    """
    serializer_class = AdminUserListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if not self.request.user.is_admin_user:
            return User.objects.none()
        
        queryset = User.objects.all()
        
        # Filtros desde query params
        user_type = self.request.query_params.get('user_type')
        is_active = self.request.query_params.get('is_active')
        is_verified = self.request.query_params.get('is_verified')
        search = self.request.query_params.get('search')
        
        if user_type:
            queryset = queryset.filter(user_type=user_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if is_verified is not None:
            queryset = queryset.filter(is_restaurant_verified=is_verified.lower() == 'true')
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search)
            )
        
        return queryset.order_by('-created_at')