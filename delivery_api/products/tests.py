from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase

from users.models import User
from .models import Product, RestaurantCategory
from .serializers import ProductCreateSerializer, ProductListSerializer


class ProductSerializerTests(APITestCase):
    def test_product_list_serializer_declares_average_rating(self):
        serializer = ProductListSerializer()

        self.assertIn('average_rating', serializer.fields)

    def test_product_category_must_belong_to_restaurant(self):
        restaurant = User.objects.create_user(
            username='restaurant',
            password='pass',
            user_type='restaurant',
            restaurant_name='Restaurant',
        )
        other_restaurant = User.objects.create_user(
            username='other-restaurant',
            password='pass',
            user_type='restaurant',
            restaurant_name='Other Restaurant',
        )
        other_category = RestaurantCategory.objects.create(
            restaurant=other_restaurant,
            name='Entradas',
        )
        request = APIRequestFactory().post('/products/')
        request.user = restaurant
        serializer = ProductCreateSerializer(
            data={
                'name': 'Taco',
                'description': 'Taco al pastor',
                'price': '35.00',
                'category': other_category.id,
            },
            context={'request': request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('category', serializer.errors)

    def test_partial_update_validates_discount_against_existing_price(self):
        restaurant = User.objects.create_user(
            username='discount-restaurant',
            password='pass',
            user_type='restaurant',
            restaurant_name='Discount Restaurant',
        )
        product = Product.objects.create(
            restaurant=restaurant,
            name='Taco',
            description='Taco al pastor',
            price='35.00',
        )
        product.refresh_from_db()
        request = APIRequestFactory().patch('/products/')
        request.user = restaurant
        serializer = ProductCreateSerializer(
            instance=product,
            data={'discount_price': '40.00'},
            partial=True,
            context={'request': request},
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('discount_price', serializer.errors)


@override_settings(SECURE_SSL_REDIRECT=False)
class ProductPermissionTests(APITestCase):
    def setUp(self):
        self.restaurant = User.objects.create_user(
            username='restaurant',
            password='pass',
            user_type='restaurant',
            restaurant_name='Restaurant',
        )
        self.client_user = User.objects.create_user(
            username='client',
            password='pass',
            user_type='client',
        )
        self.category = RestaurantCategory.objects.create(
            restaurant=self.restaurant,
            name='Tacos',
        )
        self.product = Product.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name='Taco',
            description='Taco al pastor',
            price='35.00',
            is_available=True,
        )

    def test_client_cannot_update_available_product(self):
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('product-detail', args=[self.product.id]),
            {'name': 'Edited'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Taco')

    def test_client_cannot_update_active_restaurant_category(self):
        self.client.force_authenticate(self.client_user)

        response = self.client.patch(
            reverse('restaurant-category-detail', args=[self.category.id]),
            {'name': 'Edited'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Tacos')
