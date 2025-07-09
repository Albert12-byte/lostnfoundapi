"""
Test for the claims API
"""
from difflib import SequenceMatcher

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from datetime import date

from rest_framework import status
from rest_framework.test import APIClient

from core.models import(
    Claims,
    Item,
)
from item.serializers import ClaimsSerializer


def match_claim_to_item(claim,items):
    """Match claim to item based on description"""
    best_match = None
    best_ratio = 0

    for item in items:
        ratio = SequenceMatcher(None,claim.description.lower(),
                item.description.lower()).ratio()
        if ratio > best_ratio and ratio > 0.6:
            best_ratio = ratio
            best_match = item

    return best_match

def create_user(email='user@example.com', password='testpass123'):
    """Create and return a user"""
    return get_user_model().objects.create_user(email=email, password=password)

def detail_url(item_id):
    """Create and Return a recipe detail URL"""
    return reverse('item:item-detail', args=[item_id])

def create_item(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Item name',
        'description': 'A simple description',
        'status': 'lost',
        'category': 'Unknown',
        'location_last_seen': 'Unknown',
        'date_lost': date.today(),
    }
    defaults.update(params)

    item = Item.objects.create(user=user, **defaults)
    return item


def create_claim(user, **params):
    """Create and return a sample claim."""
    defaults = {
        'item': create_item(user=user),
        'status': 'pending',
        'description': 'This is a test claim',
    }
    defaults.update(params)
    claim = Claims.objects.create(user=user, **defaults)
    return claim

CLAIMS_URL = reverse('item:claims-list')


class PublicClaimsApiTest(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required for retrieving claims"""
        res = self.client.get(CLAIMS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateApiTests(TestCase):
    """Test unauthorized API requests."""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_claims_admin_only(self):
        """test for retrieving claims is admin only"""
        admin_user = create_user(email='admin@example.com', password='test123')
        admin_user.is_staff = True
        admin_user.save()
        claim1 = create_claim(user=self.user)
        claim2 = create_claim(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)
        res = self.client.get(CLAIMS_URL)
        claims = [claim2, claim1]  # Assuming claims are ordered by ID
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)
        for i, claim in enumerate(claims):
            self.assertEqual(res.data[i]['description'], claim.description)
            self.assertEqual(res.data[i]['user'], claim.user.id)

    def test_claim_list_limited_to_user(self):
        """Test list of claims is limited to authenticated user"""
        other_user = create_user(email="other@example.com", password='test123')
        create_claim(user=other_user)
        create_claim(user=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        res = self.client.get(CLAIMS_URL)
        claims = Claims.objects.filter(user=self.user)
        serializer = ClaimsSerializer(claims, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), len(serializer.data))
        self.assertEqual(sorted(res.data, key=lambda x: x['id']),
                         sorted(serializer.data, key=lambda x: x['id']))

    def test_create_claim(self):
        """Test creating a claim"""
        user = get_user_model().objects.create_user(
            'testuser',
            'testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        item = create_item(user=user, title='Sample Item')
        payload = {
            'item': item.title,
            'description': 'This is a test claim',
        }
        res = self.client.post(CLAIMS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        claim = Claims.objects.get(id=res.data['id'])
        self.assertEqual(claim.item.title, payload['item'])
        self.assertEqual(claim.description, payload['description'])
        self.assertEqual(claim.user, self.user)
        self.assertEqual(claim.status, 'pending')


    def test_update_claim_status_admin(self):
        """Test for only admin can update status of claim"""
        admin_user = create_user(email='admin4@example.com', password='test123')
        admin_user.is_staff = True
        admin_user.save()
        claim = create_claim(user=self.user)

        self.client = APIClient()
        self.client.force_authenticate(user=admin_user)

        payload = {'status': 'approved'}
        res = self.client.patch(f'{ CLAIMS_URL}{claim.id}/', payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        claim.refresh_from_db()
        self.assertEqual(claim.status, payload['status'])

    def test_user_cant_update_claim_status(self):
        """Test user can't update claim status"""
        claim = create_claim(user=self.user)
        payload = {'status': 'cancelled'}
        res = self.client.patch(f'{CLAIMS_URL}{claim.id}/', payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_match_claim_to_item_by_description(self):
        """Test matching claim to item by description similarity"""
        item1 = create_item(user=self.user, description='A black oppo A22 with cracked screen')
        item2 = create_item(self.user, description='A white Iphone 13 with no issues')
        claim = create_claim(user=self.user, description='Black oppo A22 cracked screen found')

        items= Item.objects.all()
        matched_item = match_claim_to_item(claim,items)

        self.assertEqual(matched_item.id, item1.id)
        self.assertNotEqual(matched_item.id, item2.id)

    def test_delete_own_claim(self):
        """Test deleting own claim"""
        claim = create_claim(user=self.user)
        res = self.client.delete(f'{CLAIMS_URL}{claim.id}/')

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        exists = Claims.objects.filter(id=claim.id).exists()
        self.assertFalse(exists)

    def test_delete_other_user_claim(self):
        """Test deleting other user's claim"""
        other_user = create_user(email='other@example.com', password='test123')
        claim = create_claim(user=other_user)
        res = self.client.delete(f'{CLAIMS_URL}{claim.id}/')

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        exists = Claims.objects.filter(id=claim.id).exists()
        self.assertTrue(exists)
