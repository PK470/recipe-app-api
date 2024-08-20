"""
test for the ingredient api
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer
from recipe.tests.test_tags_api import create_user


INGREDIENT_URL = reverse('recipe:ingredient-list')

def detail_url(id):
    """create and return a detail url for ingredient"""
    return reverse('recipe:ingredient-detail', args=[id])


class PublicIngredientApiTests(TestCase):
    """Test unauthenticated api requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required"""
        res = self.client.get(INGREDIENT_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateIngredientApitest(TestCase):
    """Test unauthenticated api requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrive_ingredient(self):
        """Test retrieving a list of ingredients"""
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENT_URL)
        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredient_limited_to_user(self):
        """Test that ingredients returned are for the authenticated user"""
        user2 = create_user(email='user2@example.com')
        Ingredient.objects.create(user=user2, name='Veggie')
        ingredient2 = Ingredient.objects.create(user=self.user, name='salt')

        res = self.client.get(INGREDIENT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient2.name)
        self.assertEqual(res.data[0]['id'], ingredient2.id)

    def test_update_ingredient(self):
        """Test updating an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Kale')
        payload = {'name': 'Spinach'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test deleting an ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Kale')
        url = detail_url(ingredient.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        ingredient = Ingredient.objects.filter(user = self.user)
        self.assertFalse(ingredient.exists())

    def test_filter_ingredients_assign_to_recipe(self):
        """Test filtering ingredients by those assigned to a recipe"""
        in1 = Ingredient.objects.create(user = self.user, name = 'Apple')
        in2 = Ingredient.objects.create(user = self.user, name = 'Banana')
        recipe = Recipe.objects.create(
            user = self.user, 
            title = 'Test Recipe',
            time_minutes = 10,
            price = 5.00,
        )
        recipe.ingredient.add(in1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})
        
        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)        

    def test_filtered_ingredients_unique(self):
        """Test filtering ingredients by assigned to recipe returns unique items"""
        in1 = Ingredient.objects.create(user = self.user, name = 'Apple')
        Ingredient.objects.create(user = self.user, name='banana')
        recipe1 = Recipe.objects.create(
            user = self.user, 
            title = 'Test1 Recipe',
            time_minutes = 10,
            price = 5.00,
        )
        recipe2 = Recipe.objects.create(
            user = self.user, 
            title = 'Test2 Recipe',
            time_minutes = 10,
            price = 5.00,
        )
        recipe1.ingredient.add(in1)
        recipe2.ingredient.add(in1)

        res = self.client.get(INGREDIENT_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)