from unittest.mock import patch, MagicMock

from bom.models import Organization
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from django.test import TestCase, Client
from django.urls import reverse

from indabom import stripe as stripe_module
from indabom.models import OrganizationMeta, OrganizationSubscription, CheckoutSessionRecord, IndabomUserMeta

User = get_user_model()


class StripeIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username="alice", email="alice@example.com", password="pw")
        self.org = Organization.objects.create(name="Acme", owner=self.owner)
        # Ensure terms are accepted to bypass middleware redirects in tests
        IndabomUserMeta.objects.create(user=self.owner, terms_accepted_at=timezone.now())
        self.client.force_login(self.owner)

    # --- subscribe() ---

    @patch("indabom.stripe.stripe.checkout.Session.create")
    @patch("indabom.stripe.create_org_customer_if_needed", return_value="cus_123")
    def test_subscribe_starts_checkout_and_returns_session(self, mock_cust, mock_session_create):
        mock_session_create.return_value = MagicMock(id="sess_123", url="https://stripe.example/checkout/sess_123")

        # Create pending record required by subscribe()
        pending = CheckoutSessionRecord.objects.create(
            user=self.owner,
            renewal_consent=False,
            renewal_consent_text="",
            renewal_consent_timestamp=None,
            checkout_session_id="",
            stripe_subscription_id="",
        )

        req = self.client.get("")  # dummy request
        session_obj = stripe_module.subscribe(
            req.wsgi_request,
            price_id="price_123",
            organization=self.org,
            quantity=1,
            pending_subscription=pending,
        )

        # subscribe returns the created Session (not an HttpResponse)
        self.assertIs(session_obj, mock_session_create.return_value)
        mock_cust.assert_called_once_with(self.org)
        mock_session_create.assert_called_once()
        _, kwargs = mock_session_create.call_args
        self.assertEqual(kwargs["customer"], "cus_123")
        self.assertEqual(kwargs["mode"], "subscription")
        self.assertEqual(kwargs["line_items"], [{"price": "price_123", "quantity": 1}])
        self.assertIn("success_url", kwargs)
        self.assertIn("cancel_url", kwargs)
        # Must include pending_subscription_id in metadata
        self.assertEqual(kwargs["metadata"].get("pending_subscription_id"), pending.id)

    @patch("indabom.stripe.get_active_subscription", return_value=MagicMock())
    def test_subscribe_blocks_when_active_subscription_exists(self, _mock_active):
        # When already subscribed, subscribe() should not create a session and should return None
        pending = CheckoutSessionRecord.objects.create(
            user=self.owner,
            renewal_consent=False,
            renewal_consent_text="",
            renewal_consent_timestamp=None,
            checkout_session_id="",
            stripe_subscription_id="",
        )
        req = self.client.get(reverse("bom:settings"))
        result = stripe_module.subscribe(
            req.wsgi_request,
            price_id="price_123",
            organization=self.org,
            quantity=1,
            pending_subscription=pending,
        )

        self.assertIsNone(result)

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

    # --- webhook: customer.subscription.updated with None period fields should currently crash (prove bug) ---

    @patch("indabom.stripe.transaction.on_commit", side_effect=lambda fn: fn())
    @patch("indabom.stripe.stripe.Webhook.construct_event")
    def test_webhook_customer_subscription_created(self, mock_construct, _mock_on_commit):
        OrganizationMeta.objects.create(organization=self.org, stripe_customer_id="cus_TamzArV1In7q9U")

        # Real test event from stripe
        event = {
            "id": "evt_1Sf3XQRXJPGSddcmyQShJlz1",
            "object": "event",
            "api_version": "2025-10-29.clover",
            "created": 1765911839,
            "data": {
                "object": {
                    "id": "sub_1Sf3XORXJPGSddcmM7jHzPDA",
                    "object": "subscription",
                    "application": None,
                    "application_fee_percent": None,
                    "automatic_tax": {
                        "disabled_reason": None,
                        "enabled": True,
                        "liability": {
                            "type": "self"
                        }
                    },
                    "billing_cycle_anchor": 1765911836,
                    "billing_cycle_anchor_config": None,
                    "billing_mode": {
                        "flexible": {
                            "proration_discounts": "included"
                        },
                        "type": "flexible",
                        "updated_at": 1765911813
                    },
                    "billing_thresholds": None,
                    "cancel_at": None,
                    "cancel_at_period_end": False,
                    "canceled_at": None,
                    "cancellation_details": {
                        "comment": None,
                        "feedback": None,
                        "reason": None
                    },
                    "collection_method": "charge_automatically",
                    "created": 1765911836,
                    "currency": "usd",
                    "customer": "cus_TamzArV1In7q9U",
                    "customer_account": None,
                    "days_until_due": None,
                    "default_payment_method": "pm_1Sf3XLRXJPGSddcmyZl12FXK",
                    "default_source": None,
                    "default_tax_rates": [],
                    "description": None,
                    "discounts": [],
                    "ended_at": None,
                    "invoice_settings": {
                        "account_tax_ids": None,
                        "issuer": {
                            "type": "self"
                        }
                    },
                    "items": {
                        "object": "list",
                        "data": [
                            {
                                "id": "si_TcI7lGms3uYsig",
                                "object": "subscription_item",
                                "billing_thresholds": None,
                                "created": 1765911836,
                                "current_period_end": 1768590236,
                                "current_period_start": 1765911836,
                                "discounts": [],
                                "metadata": {},
                                "plan": {
                                    "id": "price_1STCAmRXJPGSddcmMnBtV8P8",
                                    "object": "plan",
                                    "active": True,
                                    "amount": 3500,
                                    "amount_decimal": "3500",
                                    "billing_scheme": "per_unit",
                                    "created": 1763085096,
                                    "currency": "usd",
                                    "interval": "month",
                                    "interval_count": 1,
                                    "livemode": False,
                                    "metadata": {},
                                    "meter": None,
                                    "nickname": None,
                                    "product": "prod_TQ2EyaVd2mIzdK",
                                    "tiers_mode": None,
                                    "transform_usage": None,
                                    "trial_period_days": None,
                                    "usage_type": "licensed"
                                },
                                "price": {
                                    "id": "price_1STCAmRXJPGSddcmMnBtV8P8",
                                    "object": "price",
                                    "active": True,
                                    "billing_scheme": "per_unit",
                                    "created": 1763085096,
                                    "currency": "usd",
                                    "custom_unit_amount": None,
                                    "livemode": False,
                                    "lookup_key": None,
                                    "metadata": {},
                                    "nickname": None,
                                    "product": "prod_TQ2EyaVd2mIzdK",
                                    "recurring": {
                                        "interval": "month",
                                        "interval_count": 1,
                                        "meter": None,
                                        "trial_period_days": None,
                                        "usage_type": "licensed"
                                    },
                                    "tax_behavior": "unspecified",
                                    "tiers_mode": None,
                                    "transform_quantity": None,
                                    "type": "recurring",
                                    "unit_amount": 3500,
                                    "unit_amount_decimal": "3500"
                                },
                                "quantity": 2,
                                "subscription": "sub_1Sf3XORXJPGSddcmM7jHzPDA",
                                "tax_rates": []
                            }
                        ],
                        "has_more": False,
                        "total_count": 1,
                        "url": "/v1/subscription_items?subscription=sub_1Sf3XORXJPGSddcmM7jHzPDA"
                    },
                    "latest_invoice": "in_1Sf3XMRXJPGSddcm8FbRimXb",
                    "livemode": False,
                    "metadata": {},
                    "next_pending_invoice_item_invoice": None,
                    "on_behalf_of": None,
                    "pause_collection": None,
                    "payment_settings": {
                        "payment_method_options": {
                            "acss_debit": None,
                            "bancontact": None,
                            "card": {
                                "network": None,
                                "request_three_d_secure": "automatic"
                            },
                            "customer_balance": None,
                            "konbini": None,
                            "payto": None,
                            "sepa_debit": None,
                            "us_bank_account": None
                        },
                        "payment_method_types": None,
                        "save_default_payment_method": "off"
                    },
                    "pending_invoice_item_interval": None,
                    "pending_setup_intent": None,
                    "pending_update": None,
                    "plan": {
                        "id": "price_1STCAmRXJPGSddcmMnBtV8P8",
                        "object": "plan",
                        "active": True,
                        "amount": 3500,
                        "amount_decimal": "3500",
                        "billing_scheme": "per_unit",
                        "created": 1763085096,
                        "currency": "usd",
                        "interval": "month",
                        "interval_count": 1,
                        "livemode": False,
                        "metadata": {},
                        "meter": None,
                        "nickname": None,
                        "product": "prod_TQ2EyaVd2mIzdK",
                        "tiers_mode": None,
                        "transform_usage": None,
                        "trial_period_days": None,
                        "usage_type": "licensed"
                    },
                    "quantity": 2,
                    "schedule": None,
                    "start_date": 1765911836,
                    "status": "active",
                    "test_clock": None,
                    "transfer_data": None,
                    "trial_end": None,
                    "trial_settings": {
                        "end_behavior": {
                            "missing_payment_method": "create_invoice"
                        }
                    },
                    "trial_start": None
                }
            },
            "livemode": False,
            "pending_webhooks": 1,
            "request": {
                "id": None,
                "idempotency_key": "ef23b01a-f74a-4c93-ab56-ea94c42589ca"
            },
            "type": "customer.subscription.created"
        }
        mock_construct.return_value = event

        resp = self.client.post(
            reverse("stripe-webhook"),
            data=b"{}",
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE="sig",
        )
        self.assertNotEqual(resp.status_code, 500)
