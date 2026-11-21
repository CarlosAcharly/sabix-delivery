from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase


User = get_user_model()


class RestaurantLocationProfileTests(APITestCase):
    def setUp(self):
        self.restaurant = User.objects.create_user(
            username='location-restaurant',
            password='test-password',
            user_type='restaurant',
        )
        self.client.force_authenticate(self.restaurant)

    def test_restaurant_can_save_and_read_current_location(self):
        response = self.client.patch(
            reverse('profile'),
            {
                'current_location_lat': '19.4326000',
                'current_location_lng': '-99.1332000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.current_location_lat, Decimal('19.4326000'))
        self.assertEqual(self.restaurant.current_location_lng, Decimal('-99.1332000'))

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_location_lat'], '19.4326000')
        self.assertEqual(response.data['current_location_lng'], '-99.1332000')

    def test_restaurant_location_coordinates_are_range_checked(self):
        response = self.client.patch(
            reverse('profile'),
            {'current_location_lat': '91'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)


class DeliveryLocationProfileTests(APITestCase):
    def setUp(self):
        self.delivery_person = User.objects.create_user(
            username='location-courier',
            password='test-password',
            user_type='delivery',
        )
        self.client.force_authenticate(self.delivery_person)

    def test_delivery_person_can_save_and_read_current_location(self):
        response = self.client.patch(
            reverse('profile'),
            {
                'current_location_lat': '19.4326000',
                'current_location_lng': '-99.1332000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.delivery_person.refresh_from_db()
        self.assertEqual(
            self.delivery_person.current_location_lat,
            Decimal('19.4326000'),
        )
        self.assertEqual(
            self.delivery_person.current_location_lng,
            Decimal('-99.1332000'),
        )

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['current_location_lat'], '19.4326000')
        self.assertEqual(response.data['current_location_lng'], '-99.1332000')
