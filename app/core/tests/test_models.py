"""
Tests for models
"""
from unittest.mock import patch
from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model

from core import models



def create_user(email="user@example.com", password='testpass123'):
    """Create and return a new user."""
    return get_user_model().objects.create_user(email, password)


class ModelTests(TestCase):
    """Test Models"""

    def test_create_user_with_email_successful(self):
        """Test creating a user eith an email is successful"""
        email = 'test@example.com'
        password = 'testpass123'
        user = get_user_model().objects.create_user(
            email=email,
            password=password,
        )

        self.assertEqual(user.email, email)
        self.assertTrue(user.check_password(password))

    def test_new_user_email_normalised(self):
        """test email is normalised for new users"""
        sample_emails = [
            ['test1@EXAMPLE.com', 'test1@example.com'],
            ['Test2@Example.com', 'Test2@example.com'],
            ['TEST3@EXAMPLE.COM', 'TEST3@example.com'],
            ['test4@example.COM', 'test4@example.com'],
        ]
        for email, expected in sample_emails:
            user = get_user_model().objects.create_user(email, 'sample123')
            self.assertEqual(user.email, expected)

    def test_new_user_without_email_raises_error(self):
        """Test that creating a user without an email raises a valueError"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_user('', 'test123')

    def test_create_superuser(self):
        """Test creating a superuser"""
        user = get_user_model().objects.create_superuser(
            'test@example.com',
            'test123',
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_create_item(self):
        """test creating a recipe is successful"""
        user = get_user_model().objects.create_user(
            'test@example.com'
            'testpass123'
        )
        lost_status = 'lost'
        item_category = 'electronics'
        item = models.Item.objects.create(
            user=user,
            title='Item name',
            description= 'Item description',
            status = lost_status,
            category= item_category,
            location_last_seen = "C-Block",
            date_lost =date.today(),
        )

        self.assertEqual(str(item), item.title)

    def test_test_create_tag(self):
        """Test creating a  tag is successful"""

        user = create_user()
        tag = models.Tag.objects.create(user=user, name='Tag1')

        self.assertEqual(str(tag), tag.name)

    def test_create_claim(self):
        """Test creating a claim is successful"""
        user = create_user()
        lost_status = 'found'
        item_category ='Jewellry'
        item = models.Item.objects.create(
            user=user,
            title='Item name',
            description= 'Item description',
            status = lost_status,
            category= item_category,
            location_last_seen = "C-Block",
            date_lost =date.today(),

        )
        claim = models.Claims.objects.create(
            user=user,
            item=item,
            status='pending',
            description='This is a test claim'
        )
        self.assertEqual(str(claim), str(claim.item))
        self.assertEqual(claim.user, user)
        self.assertEqual(claim.item, item)
        self.assertEqual(claim.status, 'pending')
        self.assertEqual(claim.description, 'This is a test claim')


    @patch('core.models.uuid.uuid4')
    def test_item_file_name__uuid(self, mock_uuid):
        """Test generating image path."""
        uuid = 'test-uuid'
        mock_uuid.return_value = uuid
        file_path = models.item_image_file_path(None, 'example.jpg')

        self.assertEqual(file_path,f'uploads/item/{uuid}.jpg')
