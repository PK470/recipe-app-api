"""
Test for the tags of APIs.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe

from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    """create and return the tag url"""
    return reverse('recipe:tag-detail', args=[tag_id])

def create_user(email='user@example.com', password='testpass123'):
    """create and return a user"""
    return get_user_model().objects.create_user(email=email, password=password)
    

class PublicTagsApiTests(TestCase):
    """Test unauthenticated API request"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving tags."""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateTagsApiTests(TestCase):
    """Test anuthenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrive_tags(self):
        """Test retriving a list of tags."""
        Tag.objects.create(user=self.user, name='vegan')
        Tag.objects.create(user=self.user, name='dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many = True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user"""
        user2 = create_user(email= 'user2@example.com')
        Tag.objects.create(user=user2, name='fruity')
        tag = Tag.objects.create(user = self.user, name='Confort Food')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        """test updating tag"""
        tag = Tag.objects.create(user = self.user, name='after dinner')
        payload = {'name': 'Dessert'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])
    
    def test_delete_tag(self):
        """test deleting a tag"""
        tag = Tag.objects.create(user = self.user, name='after dinner')
        url = detail_url(tag.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tag = Tag.objects.filter(user = self.user)
        self.assertFalse(tag.exists())

    def test_filter_tag_assigned_to_recipes(self):
        """Test filtering tags by those assigned to recipes"""
        tag1 = Tag.objects.create(user = self.user, name='tag1')
        tag2 = Tag.objects.create(user = self.user, name='tag2')
        recipe1 = Recipe.objects.create(
            user = self.user, 
            title = 'Test1 Recipe',
            time_minutes = 10,
            price = 5.00,
        )
        recipe1.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only':1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filterd_tags_unique(self):
        """Test filterd tags return unique list"""
        tag = Tag.objects.create(user = self.user, name='tag1')
        Tag.objects.create(user = self.user, name='Dinner')
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
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)
        res = self.client.get(TAGS_URL, {'assigned_only':1})
        self.assertEqual(len(res.data), 1)