from unittest.mock import patch, MagicMock

from bom.models import Organization
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()


class IndabomViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="kasper", email="kasper@ghost.com", password="pw12345")
        self.org = Organization.objects.create(name="Org1", owner=self.user)
        profile = self.user.bom_profile()
        profile.organization = self.org
        profile.save()
        self.other_user = User.objects.create_user(username="bob", email="bob@example.com", password="pw12345")
        other_profile = self.other_user.bom_profile()
        other_profile.organization = self.org
        other_profile.save()

    def _set_owner_to_other_user(self):
        self.org.owner = self.other_user
        self.org.save()

    # --- index ---
    def test_index_anonymous_ok(self):
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.status_code, 200)

    def test_index_authenticated_redirects_home(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("index"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("bom:home"))

    # --- signup ---
    def test_signup_get(self):
        resp = self.client.get(reverse("signup"))
        self.assertEqual(resp.status_code, 200)

    def test_signup_post_creates_and_logs_in(self):
        data = {
            "username": "charlie",
            "password1": "S3cretPass!xyz",
            "password2": "S3cretPass!xyz",
            "email": "charlie@example.com",
            "first_name": "Char",
            "last_name": "Lie",
        }
        resp = self.client.post(reverse("signup"), data)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("bom:home"))

    # --- static content pages ---
    def test_static_pages_ok(self):
        pages = [
            "about",
            "product",
            "privacy-policy",
            "terms-and-conditions",
            "install",
            "pricing",
            "checkout-success",
            "checkout-cancelled",
        ]
        for name in pages:
            resp = self.client.get(reverse(name))
            self.assertEqual((name, resp.status_code), (name, 200))

    # --- checkout (GET) branches ---
    def test_checkout_get_non_owner_redirects(self):
        self.client.force_login(self.user)
        self._set_owner_to_other_user()

        resp = self.client.get(reverse("checkout"), HTTP_REFERER=reverse("bom:settings"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("bom:settings"))

    @patch("indabom.views.stripe.get_active_subscription", return_value=MagicMock())
    def test_checkout_get_already_subscribed_redirects_manage(self, _mock_active):
        self.client.force_login(self.user)

        resp = self.client.get(reverse("checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("stripe-manage"))

    @patch("indabom.views.stripe.get_product")
    @patch("indabom.views.stripe.get_price")
    @patch("indabom.views.stripe.get_active_subscription", return_value=None)
    def test_checkout_get_renders_when_ok(self, _mock_active, mock_price, mock_product):
        self.client.force_login(self.user)

        mock_price.return_value = MagicMock(unit_amount=500, product="prod_1")
        mock_product.return_value = MagicMock()

        resp = self.client.get(reverse("checkout"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"checkout", resp.content.lower())

    # --- checkout (POST) ---
    @patch("indabom.views.stripe.subscribe", return_value=MagicMock(id="sess_1", url="/ok"))
    def test_checkout_post_valid_calls_subscribe(self, mock_subscribe):
        self.client.force_login(self.user)

        data = {
            "price_id": "price_123",
            "organization": str(self.org.pk),
            "unit": 2,
            "renewal_consent": True
        }
        resp = self.client.post(reverse("checkout"), data)
        self.assertEqual(resp.status_code, 303)
        self.assertEqual(resp.url, "/ok")
        mock_subscribe.assert_called_once()

        data = {
            "price_id": "price_123",
            "organization": str(self.org.pk),
            "unit": 2,
            "renewal_consent": False
        }
        resp = self.client.post(reverse("checkout"), data)
        self.assertEqual(resp.status_code, 200)
        mock_subscribe.assert_called_once()

    # --- stripe_manage ---
    @patch("indabom.views.stripe.manage_subscription", return_value=HttpResponseRedirect("/portal"))
    def test_stripe_manage_owner_delegates(self, mock_manage):
        self.client.force_login(self.user)

        resp = self.client.get(reverse("stripe-manage"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/portal")
        mock_manage.assert_called_once()

    def test_stripe_manage_non_owner_redirects(self):
        self.client.force_login(self.user)
        self._set_owner_to_other_user()

        resp = self.client.get(reverse("stripe-manage"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("bom:settings") + "#organization")

        resp = self.client.get(reverse("stripe-manage"), HTTP_REFERER=reverse("bom:settings"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("bom:settings"))

    # --- delete_account ---
    @patch("indabom.views.stripe.get_active_subscription", return_value=MagicMock())
    def test_delete_account_owner_with_active_subscription_redirects(self, _mock_active):
        self.client.force_login(self.user)

        resp = self.client.get(reverse("account-delete"))
        # GET shows page, but the branch for active subscription is on POST/flow? In code it redirects immediately.
        # View checks and redirects before rendering.
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("stripe-manage"))

    def test_delete_account_post_deletes_user_when_allowed(self):
        # Make user NOT owner to allow deletion
        self._set_owner_to_other_user()
        username = self.user.username
        self.client.force_login(self.user)

        resp = self.client.post(reverse("account-delete"), {"password": "pw12345"})
        self.assertEqual(resp.status_code, 200)
        # Template shows username in content
        self.assertIn(username.encode('utf-8'), resp.content)

    # --- stripe_webhook wrapper ---
    def test_stripe_webhook_get_not_allowed(self):
        resp = self.client.get(reverse("stripe-webhook"))
        self.assertEqual(resp.status_code, 405)

    @patch("indabom.views.stripe.stripe_webhook", side_effect=Exception("boom"))
    def test_stripe_webhook_failure_returns_500(self, _mock_delegate):
        resp = self.client.post(reverse("stripe-webhook"))
        self.assertEqual(resp.status_code, 500)
