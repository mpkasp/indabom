from unittest.mock import patch, Mock

from bom.models import Organization, UserMeta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountDeletionTests(TestCase):
    def setUp(self):
        # Create a base organization owner for some tests
        self.owner = User.objects.create_user(username='owner', password='ownerpass', email='owner@example.com')
        self.owner_meta = UserMeta.objects.create(user=self.owner, organization=None, role='A')
        # Owner's organization
        self.org = Organization.objects.create(name='Org Inc', subscription='F', owner=self.owner)
        self.owner_meta.organization = self.org
        self.owner_meta.save()

    def login(self, user, password):
        logged_in = self.client.login(username=user.username, password=password)
        self.assertTrue(logged_in, 'Precondition failed: could not log test user in')

    def test_non_owner_can_delete_account(self):
        # Create a regular user in the owner's org
        user = User.objects.create_user(username='member', password='memberpass', email='m@example.com')
        UserMeta.objects.create(user=user, organization=self.org, role='M')

        self.login(user, 'memberpass')

        # GET confirm page
        url = reverse('account-delete')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # POST with correct password
        resp = self.client.post(url, data={'password': 'memberpass'})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'indabom/account-deleted.html')
        self.assertFalse(User.objects.filter(id=user.id).exists())

    @patch('indabom.views.stripe.get_active_subscription')
    def test_owner_with_active_subscription_blocked_and_redirected(self, mock_active_sub):
        mock_active_sub.return_value = Mock()

        self.login(self.owner, 'ownerpass')
        url = reverse('account-delete')
        resp = self.client.get(url)
        # Should redirect to stripe-manage
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse('stripe-manage'))
        # Ensure owner and org still exist
        self.assertTrue(User.objects.filter(id=self.owner.id).exists())
        self.assertTrue(Organization.objects.filter(id=self.org.id).exists())

    @patch('indabom.views.stripe.get_active_subscription')
    def test_owner_without_active_subscription_deletes_org_and_user(self, mock_active_sub):
        mock_active_sub.return_value = None

        self.login(self.owner, 'ownerpass')
        url = reverse('account-delete')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.post(url, data={'password': 'ownerpass'})
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'indabom/account-deleted.html')
        self.assertFalse(User.objects.filter(id=self.owner.id).exists())
        self.assertFalse(Organization.objects.filter(id=self.org.id).exists())

    def test_incorrect_password_does_not_delete(self):
        # Non-owner scenario
        user = User.objects.create_user(username='member2', password='memberpass2', email='m2@example.com')
        UserMeta.objects.create(user=user, organization=self.org, role='M')

        self.login(user, 'memberpass2')
        url = reverse('account-delete')
        resp = self.client.post(url, data={'password': 'wrongpass'})
        self.assertEqual(resp.status_code, 200)
        # Should render the same confirm template due to error
        self.assertTemplateUsed(resp, 'indabom/delete-account.html')
        self.assertTrue(User.objects.filter(id=user.id).exists())
