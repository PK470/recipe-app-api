"""
Tests for recipe APIs.
"""
from decimal import Decimal
import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer

RECIPE_URL = reverse('recipe:recipe-list')

def image_upload_url(recipe_id):
    """Return URL for recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])

def detail_url(recipe_id):
    """Return recipe detail URL."""
    return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **params):
    """Create a recipe with given parameters."""
    defaults = {
        "title": "Sample recipe",
        "time_minutes": 10,
        "price": Decimal("5.50"),
        "description": "Sample recipe description",
        "link": "http://example.com/recipe",

    }
    defaults.update(params)

    recipe = Recipe.objects.create(user = user, **defaults)
    return recipe 


def create_user(**params):
    """"create and return new user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated recipe API access."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required."""
        res = self.client.get(RECIPE_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITest(TestCase):
    """Test authenticated recipe API access."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'testuser',
            'testpass'
        )
        self.client.force_authenticate(self.user)

    def test_retrive_recipe(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_recipe_list_limited_to_user(self):
        """Test retrieving a recipe list is limited to the authenticated user."""
        other_user = get_user_model().objects.create_user('otheruser@example.com', 'otherpass')
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPE_URL)

        recipe = Recipe.objects.filter(user = self.user)
        serializer = RecipeSerializer(recipe, many = True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user = self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)  
        
    def test_create_recipe(self):
        """Test creating a new recipe."""
        payload = {
            'title': 'Test recipe',
            'time_minutes': 10,
            'price': Decimal('5.00'),
        }
        res = self.client.post(RECIPE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """Test partial update of recipe"""
        original_link = 'https://example.com/recipe.pdf'
        recipe = create_recipe(
            user=self.user, title='Original Recipe', link=original_link
        )
        payload = {'title': 'New Recipe Title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)
         
    def test_full_update(self):
        """Test full update of recipe"""
        recipe = create_recipe(
            user=self.user, 
            title='Original Recipe', 
            link='https://example.com/recipe.pdf',
            description='sample recipe description',
        )
        payload = {
            'title': 'New Recipe Title',
            'link': 'https://example.con/new-recipe.pdf',
            'description':'new recipe description',
            'time_minutes': 20,
            'price': Decimal('10.00'),
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(v, getattr(recipe, k))
        self.assertEqual(recipe.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in error"""
        new_user = create_user(email='user2@example.com', password='test123')
        recipe = create_recipe(user=self.user, title='Original Recipe')
        payload = {'user':new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        """Test deleting a recipe"""
        recipe = create_recipe(user = self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_recipe_other_user_recipe_user(self):
        """Test trying to delete other's recipe gives error"""
        new_user = create_user(email='user2example.com', password='test123')
        recipe = create_recipe(user=new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tag(self):
        """Test creating a new tag"""
        payload = {
            'title': 'thai prawn curry',
            'time_minutes': 30,
            'price': Decimal('10.00'),
            'tags': [{'name': 'Thai'}, {'name': 'Prawn'}],
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.filter(user = self.user)
        self.assertEqual(recipe.count(), 1)
        recipe = recipe[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def test_creating_recipe_with_existing_tag(self):
        """Test creating a recipe with existing tag"""
        tag = Tag.objects.create(user=self.user, name='Thai')
        payload = {
            'title': 'thai prawn curry',
            'time_minutes': 30,
            'price': Decimal('10.00'),
            'tags': [{'name': 'Thai'}, {'name':'dinner'}],
        }
        res = self.client.post(RECIPE_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipe.count(), 1)
        recipe = recipe[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user
            ).exists()
            self.assertTrue(exists)

    def text_create_tag_on_update(self):
        """Test updating a recipe with a new tag"""
        recipe = create_recipe(user = self.user)
        
        payload = {'tag':[{'name':'lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user = self.user, name = 'lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """Test updating a recipe with existing tag"""
        tag = Tag.objects.create(user = self.user, name = 'break fast')
        recipe = create_recipe(user = self.user)
        recipe.tags.add(tag)

        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags':[{'name':'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """test clearing a recipe tags"""
        tag = Tag.objects.create(user = self.user, name = 'Dessert')
        recipe = create_recipe(user = self.user)
        recipe.tags.add(tag)

        payload = {
            'tags': []
        }
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)
        
    def test_create_recipe_with_new_ingredient(self):
        """Test creating a recipe with a new ingredient"""
        payload = {
            'title': 'Test Recipe',
            'time_minutes': 10,
            'price': 5.00,
            'tags': [{'name': 'break fast'}],
            'ingredient': [{'name': 'test ingredient'},{'name':'salt'}],
            }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.filter(user = self.user)
        self.assertEqual(recipe.count(), 1)
        recipe = recipe[0]
        self.assertEqual(recipe.ingredient.count(), 2)
        for ingredient in payload['ingredient']:
            exist = recipe.ingredient.filter(
                name=ingredient['name'],
                user = self.user
            ).exists()
            self.assertTrue(exist)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a recipe with an existing ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='test ingredient')
        payload = {
            'title': 'Test Recipe',
            'time_minutes': 10,
            'price': 5.00,
            'tags': [{'name': 'break fast'}],
            'ingredient': [{'name': 'test ingredient'},{'name':'salt'}],
            }
        res = self.client.post(RECIPE_URL, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipe.count(), 1)
        recipe = recipe[0]
        self.assertEqual(recipe.ingredient.count(), 2)
        self.assertIn(ingredient, recipe.ingredient.all())
        for ingredient in payload['ingredient']:
            exist = recipe.ingredient.filter(
                name=ingredient['name'],
                user = self.user
                ).exists()
            self.assertTrue(exist)

    def test_creating_ingredients_on_update(self):
        """Test creating ingredients on update"""
        recipe = create_recipe(user=self.user)
        payload = {'ingredient': [{'name': 'Limes'}],}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user = self.user, name = 'Limes')
        self.assertIn(new_ingredient, recipe.ingredient.all())
         
    def test_update_recipe_assign_ingredient(self):
        """Test updating a recipe and assigning an ingredient"""
        recipe = create_recipe(user=self.user, title='Test Recipe')
        ingredient1 = Ingredient.objects.create(user=self.user, name='Limes')
        recipe.ingredient.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='chilli')
        payload = {'ingredient':[{'name':'chilli'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(ingredient2, recipe.ingredient.all())
        self.assertNotIn(ingredient1, recipe.ingredient.all())

    def test_clear_recipe_ingredients(self):
        """Test clearing a recipe's ingredients"""
        recipe = create_recipe(user=self.user, title='Test Recipe')
        ingredient = Ingredient.objects.create(user=self.user, name='Limes')
        recipe.ingredient.add(ingredient)
        payload = {'ingredient': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredient.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering by tags"""
        recipe1 = create_recipe(user=self.user, title='Test Recipe 1')
        recipe2 = create_recipe(user=self.user, title='Test Recipe 2')
        tag1 = Tag.objects.create(user=self.user, name='Tag 1')
        tag2 = Tag.objects.create(user=self.user, name='Tag 2')
        recipe1.tags.add(tag1)
        recipe2.tags.add(tag2)
        recipe3 = create_recipe(user = self.user, title = 'Test Recipe 3')

        param = {'tags':f'{tag1.id},{tag2.id}'}
        res = self.client.get(RECIPE_URL, param)
        
        s1 = RecipeSerializer(recipe1)
        s2 = RecipeSerializer(recipe2)
        s3 = RecipeSerializer(recipe3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

    def test_filter_by_ingredients(self):
        """Test filtering recipes by ingredients."""
        r1 = create_recipe(user=self.user, title='Posh Beans on Toast')
        r2 = create_recipe(user=self.user, title='Chicken Cacciatore')
        in1 = Ingredient.objects.create(user=self.user, name='Feta Cheese')
        in2 = Ingredient.objects.create(user=self.user, name='Chicken')
        r1.ingredient.add(in1)
        r2.ingredient.add(in2)
        r3 = create_recipe(user=self.user, title='Red Lentil Daal')

        params = {'ingredient': f'{in1.id},{in2.id}'}
        res = self.client.get(RECIPE_URL, params)

        s1 = RecipeSerializer(r1)
        s2 = RecipeSerializer(r2)
        s3 = RecipeSerializer(r3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)

class ImageUploadTests(TestCase):
    """Test for the image upload functionality"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
            )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB',(10,10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image':image_file}
            res = self.client.post(url, payload, format='multipart')
        
        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.recipe.id)
        payload = {'image': 'noimage'} # This is not a valid image
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        
                
