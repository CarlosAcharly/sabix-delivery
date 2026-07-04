from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import logout
from rest_framework.permissions import AllowAny
from .models import User
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserSerializer,
    UserProfileUpdateSerializer,
    PasswordChangeSerializer,
    UserTokenRefreshSerializer
)

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

class LoginView(APIView):
    """
    Vista para iniciar sesión
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)

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
                'logout': '/api/v1/users/logout/',
                'perfil': '/api/v1/users/profile/',
                'cambiar_contraseña': '/api/v1/users/change-password/',
                'refrescar_token': '/api/v1/users/token/refresh/',
                'verificar_username': '/api/v1/users/check-username/?username=valor',
                'verificar_email': '/api/v1/users/check-email/?email=valor',
            },
            'documentacion': 'Próximamente...'
        })