from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'password2', 
            'first_name', 'last_name', 'phone', 'user_type',
            'address', 'vehicle_type', 'vehicle_plate',
            'restaurant_name', 'restaurant_description', 'restaurant_address'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        
        # Validaciones según tipo de usuario
        user_type = attrs.get('user_type')
        
        if user_type == 'delivery':
            if not attrs.get('vehicle_type'):
                raise serializers.ValidationError({"vehicle_type": "El tipo de vehículo es requerido para repartidores."})
            if not attrs.get('vehicle_plate'):
                raise serializers.ValidationError({"vehicle_plate": "La placa del vehículo es requerida."})
        
        if user_type == 'restaurant':
            if not attrs.get('restaurant_name'):
                raise serializers.ValidationError({"restaurant_name": "El nombre del restaurante es requerido."})
            if not attrs.get('restaurant_address'):
                raise serializers.ValidationError({"restaurant_address": "La dirección del restaurante es requerida."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError("Credenciales inválidas.")
        
        if not user.is_active:
            raise serializers.ValidationError("Usuario inactivo.")
        
        refresh = RefreshToken.for_user(user)
        
        return {
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'full_name', 'phone', 'user_type', 'profile_image',
            'address', 'vehicle_type', 'vehicle_plate', 'is_available',
            'restaurant_name', 'restaurant_description', 'restaurant_address',
            'is_restaurant_verified', 'is_active', 'created_at'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone', 'profile_image',
            'address', 'vehicle_type', 'vehicle_plate', 'is_available',
            'restaurant_name', 'restaurant_description', 'restaurant_address'
        ]
    
    def update(self, instance, validated_data):
        # Solo permitir actualizar campos según tipo de usuario
        user_type = instance.user_type
        
        if user_type == 'client':
            fields = ['first_name', 'last_name', 'phone', 'profile_image', 'address']
        elif user_type == 'delivery':
            fields = ['first_name', 'last_name', 'phone', 'profile_image', 
                     'vehicle_type', 'vehicle_plate', 'is_available']
        elif user_type == 'restaurant':
            fields = ['first_name', 'last_name', 'phone', 'profile_image',
                     'restaurant_name', 'restaurant_description', 'restaurant_address']
        else:
            fields = ['first_name', 'last_name', 'phone', 'profile_image']
        
        for field in fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        
        instance.save()
        return instance

class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password2 = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Las contraseñas no coinciden."})
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Contraseña actual incorrecta.")
        return value

class UserTokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()