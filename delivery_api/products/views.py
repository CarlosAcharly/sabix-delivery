from rest_framework import generics, status, permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db.models import Q
from .models import Category, RestaurantCategory, Product, ProductOption, ProductOptionChoice
from .serializers import (
    CategorySerializer, RestaurantCategorySerializer,
    ProductSerializer, ProductCreateSerializer, ProductListSerializer,
    ProductOptionSerializer, ProductOptionChoiceSerializer
)
from users.permissions import IsRestaurantUser, IsAdminUser

# =============================================
# VISTAS DE CATEGORÍAS GLOBALES (SOLO ADMIN)
# =============================================

class CategoryListCreateView(generics.ListCreateAPIView):
    """Listar y crear categorías globales (solo admin)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

class CategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Ver, actualizar y eliminar categorías globales (solo admin)"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

# =============================================
# VISTAS DE CATEGORÍAS DE RESTAURANTES
# =============================================

class RestaurantCategoryListCreateView(generics.ListCreateAPIView):
    """Listar y crear categorías de un restaurante"""
    serializer_class = RestaurantCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Si es admin, ve todas las categorías
        if self.request.user.is_admin_user:
            return RestaurantCategory.objects.all()
        # Si es restaurante, ve solo las suyas
        if self.request.user.is_restaurant_owner:
            return RestaurantCategory.objects.filter(restaurant=self.request.user)
        # Si es cliente, ve todas las categorías activas
        return RestaurantCategory.objects.filter(is_active=True)
    
    def perform_create(self, serializer):
        # Solo restaurantes pueden crear categorías
        if not self.request.user.is_restaurant_owner:
            raise permissions.PermissionDenied('Solo los restaurantes pueden crear categorías.')
        serializer.save(restaurant=self.request.user)

class RestaurantCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Ver, actualizar y eliminar categoría de restaurante"""
    queryset = RestaurantCategory.objects.all()
    serializer_class = RestaurantCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_admin_user:
            return RestaurantCategory.objects.all()
        if self.request.user.is_restaurant_owner:
            return RestaurantCategory.objects.filter(restaurant=self.request.user)
        return RestaurantCategory.objects.filter(is_active=True)

# =============================================
# VISTAS DE PRODUCTOS
# =============================================

class ProductListCreateView(generics.ListCreateAPIView):
    """Listar y crear productos"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['restaurant', 'category', 'is_available', 'is_featured', 'global_category']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'name', 'created_at', 'order']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductListSerializer
    
    def get_queryset(self):
        # Si es admin, ve todos los productos
        if self.request.user.is_admin_user:
            return Product.objects.all()
        
        # Si es restaurante, ve solo sus productos
        if self.request.user.is_restaurant_owner:
            return Product.objects.filter(restaurant=self.request.user)
        
        # Si es cliente, ve solo productos disponibles
        return Product.objects.filter(is_available=True)
    
    def perform_create(self, serializer):
        # Solo restaurantes pueden crear productos
        if not self.request.user.is_restaurant_owner:
            raise permissions.PermissionDenied('Solo los restaurantes pueden crear productos.')
        serializer.save(restaurant=self.request.user)

class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Ver, actualizar y eliminar producto"""
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return ProductSerializer
        return ProductCreateSerializer
    
    def get_queryset(self):
        if self.request.user.is_admin_user:
            return Product.objects.all()
        if self.request.user.is_restaurant_owner:
            return Product.objects.filter(restaurant=self.request.user)
        return Product.objects.filter(is_available=True)

# =============================================
# VISTAS DE PRODUCTOS POR RESTAURANTE (PÚBLICO)
# =============================================

class RestaurantProductsView(generics.ListAPIView):
    """Ver productos de un restaurante específico (público)"""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'name', 'order']
    ordering = ['category__order', 'order', 'name']
    
    def get_queryset(self):
        restaurant_id = self.kwargs.get('restaurant_id')
        return Product.objects.filter(
            restaurant_id=restaurant_id,
            is_available=True
        )

# =============================================
# VISTAS DE OPCIONES DE PRODUCTOS
# =============================================

class ProductOptionListCreateView(generics.ListCreateAPIView):
    """Listar y crear opciones de productos"""
    serializer_class = ProductOptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        product_id = self.kwargs.get('product_id')
        product = Product.objects.get(id=product_id)
        
        # Verificar permisos
        if self.request.user.is_admin_user:
            return ProductOption.objects.filter(product_id=product_id)
        if self.request.user.is_restaurant_owner:
            if product.restaurant.id != self.request.user.id:
                raise permissions.PermissionDenied('No tienes permiso para ver estas opciones.')
            return ProductOption.objects.filter(product_id=product_id)
        # Clientes ven opciones de productos disponibles
        return ProductOption.objects.filter(
            product_id=product_id,
            product__is_available=True
        )
    
    def perform_create(self, serializer):
        product_id = self.kwargs.get('product_id')
        product = Product.objects.get(id=product_id)
        
        # Verificar que el usuario sea dueño del restaurante
        if not self.request.user.is_admin_user and product.restaurant.id != self.request.user.id:
            raise permissions.PermissionDenied('No tienes permiso para añadir opciones a este producto.')
        
        serializer.save(product=product)

class ProductOptionChoiceListCreateView(generics.ListCreateAPIView):
    """Listar y crear opciones de elección"""
    serializer_class = ProductOptionChoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        option_id = self.kwargs.get('option_id')
        option = ProductOption.objects.get(id=option_id)
        
        # Verificar permisos
        if self.request.user.is_admin_user:
            return ProductOptionChoice.objects.filter(option_id=option_id)
        if self.request.user.is_restaurant_owner:
            if option.product.restaurant.id != self.request.user.id:
                raise permissions.PermissionDenied('No tienes permiso para ver estas opciones.')
            return ProductOptionChoice.objects.filter(option_id=option_id)
        # Clientes ven opciones de productos disponibles
        return ProductOptionChoice.objects.filter(
            option_id=option_id,
            option__product__is_available=True
        )
    
    def perform_create(self, serializer):
        option_id = self.kwargs.get('option_id')
        option = ProductOption.objects.get(id=option_id)
        
        # Verificar que el usuario sea dueño del restaurante
        if not self.request.user.is_admin_user and option.product.restaurant.id != self.request.user.id:
            raise permissions.PermissionDenied('No tienes permiso para añadir opciones a este producto.')
        
        serializer.save(option=option)

# =============================================
# VISTAS DE BÚSQUEDA Y EXPLORACIÓN
# =============================================

class ProductSearchView(generics.ListAPIView):
    """Búsqueda global de productos (público)"""
    serializer_class = ProductListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'restaurant__restaurant_name']
    ordering_fields = ['price', 'name', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Product.objects.filter(is_available=True)
        
        # Filtros opcionales
        restaurant_id = self.request.query_params.get('restaurant')
        category_id = self.request.query_params.get('category')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        is_vegetarian = self.request.query_params.get('is_vegetarian')
        is_vegan = self.request.query_params.get('is_vegan')
        
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        if is_vegetarian and is_vegetarian.lower() == 'true':
            queryset = queryset.filter(is_vegetarian=True)
        if is_vegan and is_vegan.lower() == 'true':
            queryset = queryset.filter(is_vegan=True)
        
        return queryset