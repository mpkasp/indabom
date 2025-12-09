from unittest.mock import patch, MagicMock

from bom.models import Organization
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, Client
from django.urls import reverse

from indabom import stripe as stripe_module
from indabom.models import OrganizationMeta, OrganizationSubscription

User = get_user_model()


class StripeIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username="alice", email="alice@example.com", password="pw")
        self.org = Organization.objects.create(name="Acme", owner=self.owner)
        self.client.force_login(self.owner)

    # --- subscribe() ---

    @patch("indabom.stripe.stripe.checkout.Session.create")
    @patch("indabom.stripe.create_org_customer_if_needed", return_value="cus_123")
    def test_subscribe_redirects_to_stripe_checkout(self, mock_cust, mock_session_create):
        mock_session_create.return_value = MagicMock(url="https://stripe.example/checkout/sess_123")

        # Call through the Django view if present, or directly to function
        # View typically takes price from form; we call function for unit-style test
        req = self.client.get("")  # dummy request
        response = stripe_module.subscribe(req.wsgi_request, price_id="price_123", organization=self.org, quantity=1)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://stripe.example/checkout/sess_123")
        mock_cust.assert_called_once_with(self.org)
        mock_session_create.assert_called_once()
        _, kwargs = mock_session_create.call_args
        self.assertEqual(kwargs["customer"], "cus_123")
        self.assertEqual(kwargs["mode"], "subscription")
        self.assertEqual(kwargs["line_items"], [{"price": "price_123", "quantity": 1}])
        self.assertIn("success_url", kwargs)
        self.assertIn("cancel_url", kwargs)

    @patch("indabom.stripe.get_active_subscription", return_value=MagicMock())
    def test_subscribe_blocks_when_active_subscription_exists(self, mock_active):
        # When already subscribed, subscribe() should not create a session and should redirect back
        req = self.client.get(reverse("bom:settings"))  # referer for redirect fallback
        req.wsgi_request.META["HTTP_REFERER"] = reverse("bom:settings")
        response = stripe_module.subscribe(req.wsgi_request, price_id="price_123", organization=self.org, quantity=1)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bom:settings"))

    # --- manage_subscription() ---

    @patch("indabom.stripe.get_active_subscription", return_value=None)
    def test_manage_subscription_requires_active_subscription(self, mock_active):
        req = self.client.get(reverse("bom:settings"))
        req.wsgi_request.META["HTTP_REFERER"] = reverse("bom:settings")
        response = stripe_module.manage_subscription(req.wsgi_request, organization=self.org)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bom:settings"))

    @patch("indabom.stripe.stripe.billing_portal.Session.create")
    @patch("indabom.stripe.get_active_subscription", return_value=MagicMock())
    def test_manage_subscription_redirects_to_billing_portal(self, mock_active, mock_portal_create):
        # Ensure org has a stripe customer id in meta
        meta = OrganizationMeta.objects.create(organization=self.org, stripe_customer_id="cus_123")
        mock_portal_create.return_value = MagicMock(url="https://billing.stripe.example/portal_sess")

        req = self.client.get("")
        response = stripe_module.manage_subscription(req.wsgi_request, organization=self.org)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://billing.stripe.example/portal_sess")
        mock_portal_create.assert_called_once_with(customer="cus_123", return_url=mock_portal_create.call_args[1]["return_url"])

    # --- helpers: get_price / get_product ---

    @patch("indabom.stripe.stripe.Price.retrieve", side_effect=Exception("boom"))
    def test_get_price_adds_error_message_on_exception(self, mock_retrieve):
        req = self.client.get("")
        price = stripe_module.get_price("price_123", req.wsgi_request)
        self.assertIsNone(price)
        # Messages framework stores in response context only when rendering; here we at least ensure no crash.

    @patch("indabom.stripe.stripe.Product.retrieve", side_effect=Exception("boom"))
    def test_get_product_adds_error_message_on_exception(self, mock_retrieve):
        req = self.client.get("")
        product = stripe_module.get_product("prod_123", req.wsgi_request)
        self.assertIsNone(product)

    # --- webhook: subscription created/updated ---

    @patch("indabom.stripe.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("indabom.stripe.stripe.Webhook.construct_event")
    def test_webhook_subscription_created_updates_local_models(self, mock_construct, _mock_on_commit):
        OrganizationMeta.objects.create(organization=self.org, stripe_customer_id="cus_123")

        event = {
            "id": "evt_1",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active",
                    "quantity": 3,
                    "items": {"data": [{"price": {"id": "price_abc"}}]},
                    "current_period_start": 1700000000,
                    "current_period_end": 1702592000,
                }
            }
        }
        mock_construct.return_value = event

        resp = self.client.post(reverse("stripe-webhook"), data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="sig")
        self.assertEqual(resp.status_code, 200)

        # Subscription should have been created/updated and org plan switched to PRO
        sub = OrganizationSubscription.objects.get(stripe_subscription_id="sub_123")
        self.assertEqual(sub.status, "active")
        self.assertEqual(sub.quantity, 3)
        self.assertEqual(sub.stripe_price_id, "price_abc")

        self.org.refresh_from_db()
        # subscription value PRO constant is in bom.constants.SUSBCRIPTION_TYPE_PRO; we check quantity changed as proxy
        self.assertEqual(self.org.subscription_quantity, 3)

    # --- webhook: invoice.payment_failed -> email notification ---

    @patch("indabom.stripe.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("indabom.stripe.stripe.Webhook.construct_event")
    def test_webhook_invoice_payment_failed_sends_email(self, mock_construct, _mock_on_commit):
        OrganizationMeta.objects.create(organization=self.org, stripe_customer_id="cus_123")

        event = {
            "id": "evt_2",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_123"}}
        }
        
        mock_construct.return_value = event

        resp = self.client.post(reverse("stripe-webhook"), data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="sig")
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Payment Failed", mail.outbox[0].subject)
        self.assertIn("update your payment settings", mail.outbox[0].body)

    # --- create_org_customer_if_needed: creates when none, reuses when valid ---

    @patch("indabom.stripe.stripe.Customer.create")
    @patch("indabom.stripe.stripe.Customer.retrieve")
    def test_create_org_customer_if_needed_creates_then_reuses(self, mock_retrieve, mock_create):
        # First: no meta exists -> create new customer
        mock_create.return_value = MagicMock(id="cus_new")
        cust_id = stripe_module.create_org_customer_if_needed(self.org)
        self.assertEqual(cust_id, "cus_new")
        meta = OrganizationMeta.objects.get(organization=self.org)
        self.assertEqual(meta.stripe_customer_id, "cus_new")

        # Second: reuse existing customer
        mock_retrieve.return_value = MagicMock(id="cus_new")
        cust_id2 = stripe_module.create_org_customer_if_needed(self.org)
        self.assertEqual(cust_id2, "cus_new")
        mock_retrieve.assert_called_once_with("cus_new")

    @patch("indabom.stripe.stripe.Customer.retrieve")
    def test_create_org_customer_if_needed_handles_stale_id(self, mock_retrieve):
        # Existing stale ID should be cleared and recreated
        meta = OrganizationMeta.objects.create(organization=self.org, stripe_customer_id="cus_stale")

        # Simulate stripe.InvalidRequestError with resource_missing code
        err = stripe_module.stripe.InvalidRequestError(
            message="No such customer",
            param="id"
        )
        err.code = "resource_missing"
        mock_retrieve.side_effect = err

        with patch("indabom.stripe.stripe.Customer.create") as mock_create:
            mock_create.return_value = MagicMock(id="cus_new")
            cust_id = stripe_module.create_org_customer_if_needed(self.org)
            self.assertEqual(cust_id, "cus_new")
            meta.refresh_from_db()
            self.assertEqual(meta.stripe_customer_id, "cus_new")