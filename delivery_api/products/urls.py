from django.urls import path
from .views import (
    CategoryListCreateView, CategoryDetailView,
    RestaurantCategoryListCreateView, RestaurantCategoryDetailView,
    ProductListCreateView, ProductDetailView,
    RestaurantProductsView, ProductSearchView,
    ProductOptionListCreateView, ProductOptionChoiceListCreateView
)

urlpatterns = [
    # =============================================
    # CATEGORÍAS GLOBALES (SOLO ADMIN)
    # =============================================
    path('admin/categories/', CategoryListCreateView.as_view(), name='category-list'),
    path('admin/categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # =============================================
    # CATEGORÍAS DE RESTAURANTES
    # =============================================
    path('restaurant-categories/', RestaurantCategoryListCreateView.as_view(), name='restaurant-category-list'),
    path('restaurant-categories/<int:pk>/', RestaurantCategoryDetailView.as_view(), name='restaurant-category-detail'),
    
    # =============================================
    # PRODUCTOS
    # =============================================
    path('products/', ProductListCreateView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    
    # =============================================
    # PRODUCTOS POR RESTAURANTE (PÚBLICO)
    # =============================================
    path('restaurants/<int:restaurant_id>/products/', RestaurantProductsView.as_view(), name='restaurant-products'),
    
    # =============================================
    # BÚSQUEDA GLOBAL
    # =============================================
    path('search/', ProductSearchView.as_view(), name='product-search'),
    
    # =============================================
    # OPCIONES DE PRODUCTOS
    # =============================================
    path('products/<int:product_id>/options/', ProductOptionListCreateView.as_view(), name='product-option-list'),
    path('options/<int:option_id>/choices/', ProductOptionChoiceListCreateView.as_view(), name='product-option-choice-list'),
]