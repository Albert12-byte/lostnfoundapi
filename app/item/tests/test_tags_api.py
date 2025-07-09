"""
Tests for the tags API
"""
from datetime import date
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Tag,
    Item,
)

from item.serializers import TagSerializer


TAGS_URL = reverse('item:tag-list')

def detail_url(tag_id):
    """Create and return a tag detail url"""
    return reverse('item:tag-detail',args=[tag_id])

def create_user(email='user@example.com', password='testpass123'):
    """Create and return a user"""
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsApiTests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ Test auth is required for retrieving tags."""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """Test retrieving a list of tags"""
        Tag.objects.create(user=self.user, name='Lost Phone')
        Tag.objects.create(user=self.user, name='Electronics')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """Test list of tags is limited to authenticated user"""
        user2 = create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name='ID cards')
        tag = Tag.objects.create(user=self.user, name='Keys')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]['id'], tag.id)

    def test_update_tag(self):
        """Test updating a tag"""
        tag = Tag.objects.create(user=self.user, name = 'Wallet')

        payload = {'name':'Phones'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """test deleting a tag"""
        tag = Tag.objects.create(user=self.user, name= 'Scarf')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assigned_to_items(self):
        """test listing tags to those assigned to items"""
        tag1=Tag.objects.create(user=self.user, name='Ring')
        tag2=Tag.objects.create(user=self.user, name='Stanley cup')
        item = Item.objects.create(
            title= 'missing earbuds',
            description='lost earbuds',
            status= 'found',
            category= 'electronics',
            location_last_seen= 'Around C block',
            date_lost= date.today(),
            user=self.user,
        )
        item.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """test filtered tags returns a unique list"""
        tag = Tag.objects.create(user=self.user, name='Accessories')
        Tag.objects.create(user=self.user, name='Samsung')
        item1 = Item.objects.create(
            title= 'missing earbuds',
            description='lost earbuds',
            status= 'found',
            category= 'electronics',
            location_last_seen= 'Around C block',
            date_lost= date.today(),
            user=self.user,
        )
        item2=Item.objects.create(
             title= 'Samsung S25',
            description='lost samsung phone',
            status= 'lost',
            category= 'electronics',
            location_last_seen= 'Around Bush Canteen',
            date_lost= date.today(),
            user=self.user,
        )
        item1.tags.add(tag)
        item2.tags.add(tag)

        res = self.client.get(TAGS_URL,{'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
