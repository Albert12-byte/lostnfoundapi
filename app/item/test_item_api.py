"""
Test for item api
"""
import tempfile
import os

from PIL import Image
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient


from core.models import (
    Item,
    Tag,
)


from item.serializers import(
    ItemSerializer,
    ItemDetailSerializer,
)


ITEMS_URL = reverse('item:item-list')


def image_upload_url(item_id):
    """Create and return an image upload URL """
    return reverse('item:item-upload-image', args=[item_id])


def detail_url(item_id):
    """Create and Return a item detail URL"""
    return reverse('item:item-detail', args=[item_id])


def create_item(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Item name',
        'description': 'A simple description',
        'status': 'lost',
        'category': 'Unknown',
        'location_last_seen': 'Unknown',
        'date_lost':date.today(),
    }
    defaults.update(params)

    item = Item.objects.create(user=user, **defaults)
    return item


def create_user(**params):
    """Create and return a new user"""
    return get_user_model().objects.create_user(**params)


class PublicItemAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(ITEMS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateItemAPITests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = create_user(email='user@example.com', password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_items(self):
        """Test for retrieving items."""
        create_item(user=self.user)
        create_item(user=self.user)

        res = self.client.get(ITEMS_URL)

        items = Item.objects.all().order_by('-id')
        serializer = ItemSerializer(items, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


    def test_item_list_limited_to_user(self):
        """Test list of recipies is limited to authenticated user"""
        other_user = create_user(email="other@example.com", password='test123')
        create_item(user=other_user)
        create_item(user=self.user)

        res = self.client.get(ITEMS_URL)

        items = Item.objects.filter(user=self.user)
        serializer = ItemSerializer(items, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


    def test_get_item_detail(self):
        """Test get Item detail"""
        item = create_item(user=self.user)

        url = detail_url(item.id)
        res = self.client.get(url)

        serializer = ItemDetailSerializer(item)
        self.assertEqual(res.data, serializer.data)

    def test_create_item(self):
        """test creating an item"""
        payload = {
            'title':'Lost Samsung A22',
            'description' : 'A black samsung A22 with cracked screen',
            'status': 'lost',
            'category': 'electronics',
            'location_last_seen': 'Around G block',
            'date_lost': date.today(),
        }
        res = self.client.post(ITEMS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        item = Item.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(item, k), v)
        self.assertEqual(item.user, self.user)

    def test_partial_update_status(self):
        """Test partial update of an item's status"""
        item = create_item(
            user=self.user,
            title='Lost Item',
            description='A lost airpod',
            status='lost',
            category='electronics',
            location_last_seen= 'Around G block',
            date_lost=date.today()
        )

        payload = {'status': 'found'}
        url = reverse('item:item-detail', args=[item.id])
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        updated_item = Item.objects.get(id=item.id)
        self.assertEqual(updated_item.status, 'found')
        self.assertEqual(updated_item.title, 'Lost Item')

    def test_full_update(self):
        """test full update of recipe"""
        item = create_item(
            user=self.user,
            title='Lost Item',
            description='A lost airpod',
            status='lost',
            category='electronics',
            location_last_seen= 'Around G block',
            date_lost=date.today()
        )

        payload ={
            'title':'A new Item',
            'description':'A lost earring',
            'status': 'lost',
            'category': 'clothing',
            'location_last_seen': 'Around G block',
            'date_lost': date.today()
        }

        url = detail_url(item.id)
        res = self.client.put(url,payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        for k, v in payload.items():
            self.assertEqual(getattr(item, k), v)
        self.assertEqual(item.user, self.user)

    def test_update_user_returns_error(self):
        """Test changing the recipe user results in an error"""
        new_user = create_user(email='user2@example.com', password='test123')
        item = create_item(user=self.user)

        payload = { 'user': new_user.id}
        url = detail_url(item.id)
        self.client.patch(url, payload)

        item.refresh_from_db()
        self.assertEqual(item.user, self.user)

    def test_delete_item(self):
        """test deleting  an item successful"""
        item = create_item(user=self.user)

        url = detail_url(item.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Item.objects.filter(id=item.id).exists())

    def test_item_other_users_item_error(self):
        """Test trying to delete another users items gives error"""
        new_user = create_user(email='user2@example.com',password='test123')
        item = create_item(user= new_user)

        url = detail_url(item.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Item.objects.filter(id=item.id).exists())

    def test_create_item_with_new_tags(self):
        """Test creating a recipe with new tag."""
        payload ={
            'title':'I lost my earing',
            'description':'A lost earring',
            'status': 'lost',
            'category': 'clothing',
            'location_last_seen': 'Around G block',
            'date_lost': date.today(),
            'tags': [{'name':'earing'}, {'name':'clothing'}]

        }
        res = self.client.post(ITEMS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        items = Item.objects.filter(user=self.user)
        self.assertEqual(items.count(), 1)
        item = items[0]
        self.assertEqual(item.tags.count(), 2)
        for tag in payload['tags']:
            exists = item.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_item_with_existing_tags(self):
        """Test creating a recipe with existing tag"""
        tag_electronics = Tag.objects.create(user=self.user, name='electronics')
        payload ={
            'title':' missing earbuds',
            'description':'lost earbuds',
            'status': 'found',
            'category': 'electronics',
            'location_last_seen': 'Around C block',
            'date_lost': date.today(),
            'tags': [{'name':'earbuds'}, {'name':'electronics'}],
        }
        res = self.client.post(ITEMS_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        items = Item.objects.filter(user=self.user)
        item = items[0]
        self.assertEqual(item.tags.count(), 2)
        self.assertIn(tag_electronics,item.tags.all())
        for tag in payload['tags']:
            exists = item.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """Test creating tag when updating a recipe."""
        item = create_item(user=self.user)

        payload = {'tags': [{'name': 'Jewellry'}]}
        url = detail_url(item.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Jewellry')
        self.assertIn(new_tag, item.tags.all())

    def test_update_item_assign_tag(self):
        """Test assigning an existing rag when updating a recipe"""
        tag_electronics = Tag.objects.create(user= self.user, name='Electronics')
        item = create_item(user=self.user)
        item.tags.add(tag_electronics)

        tag_jewellry = Tag.objects.create(user=self.user, name='Jewellry')
        payload = { 'tags': [{ 'name': 'Jewellry'}]}
        url = detail_url(item.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_jewellry, item.tags.all())
        self.assertNotIn(tag_electronics, item.tags.all())

    def test_clear_item_tags(self):
        """Test clearing an item tags"""
        tag = Tag.objects.create(user=self.user, name="Dessert")
        item = create_item(user=self.user)
        item.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(item.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(item.tags.count(), 0)

    def test_filter_by_tags(self):
        """Test filtering items by tags"""
        item1 = create_item(user=self.user,title= 'Samsung A12')
        item2 = create_item(user=self.user, title='Iphone 16')
        tag1 = Tag.objects.create(user=self.user, name='Electronics')
        tag2 = Tag.objects.create(user=self.user,name='Iphone')
        item1.tags.add(tag1)
        item2.tags.add(tag2)
        item3 = create_item(user=self.user, title='Fish and chips')

        params = {'tags': f'{tag1.id}, {tag2.id}'}
        res = self.client.get(ITEMS_URL, params)

        s1 = ItemSerializer(item1)
        s2 = ItemSerializer(item2)
        s3 = ItemSerializer(item3)
        self.assertIn(s1.data, res.data)
        self.assertIn(s2.data, res.data)
        self.assertNotIn(s3.data, res.data)


class ImageUploadTest(TestCase):
    """Tests for the image upload API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.item = create_item(user=self.user)


    def tearDown(self):
        self.item.image.delete()

    def test_upload_image(self):
        """Test for uploading an image to an item"""
        url = image_upload_url(self.item.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB',(10,  10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.item.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.item.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading invalid image."""
        url = image_upload_url(self.item.id)
        payload = {'image': 'notanimage'}
        res = self.client.post(url, payload, format='multipart')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

