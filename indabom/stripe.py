import logging
from datetime import datetime, timezone
from typing import Optional

import stripe
from bom.constants import SUBSCRIPTION_TYPE_FREE, SUBSCRIPTION_TYPE_PRO
from bom.models import Organization
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

from indabom.settings import ROOT_DOMAIN, STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET
from .models import OrganizationMeta, OrganizationSubscription

logger = logging.getLogger(__name__)
stripe.api_key = STRIPE_SECRET_KEY


def _to_dt(ts):
    # Stripe sends seconds since epoch; adjust if already a datetime
    return ts if isinstance(ts, datetime) else datetime.fromtimestamp(ts, tz=timezone.utc)


def get_organization_meta_or_404(organization: Organization) -> OrganizationMeta:
    try:
        return organization.meta()
    except OrganizationMeta.DoesNotExist:
        return OrganizationMeta.objects.get_or_create(organization=organization)[0]


def get_active_subscription(organization: Organization) -> Optional[OrganizationSubscription]:
    """Retrieves the active local subscription object for the organization."""
    try:
        return OrganizationSubscription.objects.get(
            organization_meta__organization=organization,
            status='active'
        )
    except OrganizationSubscription.DoesNotExist:
        return None
    except OrganizationSubscription.MultipleObjectsReturned as e:
        logger.error(f"Multiple active subscriptions found for organization {organization.name} ({organization.id}).")
        raise e


# --- Stripe helpers
def get_price(price_id: str, request: HttpRequest) -> Optional[stripe.Price]:
    try:
        price = stripe.Price.retrieve(price_id)
    except stripe.StripeError as e:
        messages.error(request, f"Error fetching subscription details: {str(e)}. Please contact administrator.")
        return None
    except Exception:
        messages.error(request, "A critical error occurred while connecting to the payment service.")
        return None
    return price


def get_product(product_id: str, request: HttpRequest) -> Optional[stripe.Product]:
    try:
        product = stripe.Product.retrieve(product_id)
    except stripe.StripeError as e:
        messages.error(request, f"Error fetching subscription details: {str(e)}. Please contact administrator.")
        return None
    except Exception:
        messages.error(request, "A critical error occurred while connecting to the payment service.")
        return None
    return product


# --- Core Subscription Functions ---

def create_org_customer_if_needed(organization: Organization) -> str:
    """Ensures the organization has a Stripe Customer ID and returns it."""
    org_meta = get_organization_meta_or_404(organization)

    if org_meta.stripe_customer_id:
        try:
            stripe.Customer.retrieve(org_meta.stripe_customer_id)
            return org_meta.stripe_customer_id
        except stripe.InvalidRequestError as e:
            if e.code == 'resource_missing':
                logger.warning(
                    f"Stale Stripe customer ID '{org_meta.stripe_customer_id}' found for Org {organization.id}. Re-creating.")
                org_meta.stripe_customer_id = None
            else:
                raise e

    # Assuming organization.admin_user gives us the user to use for billing contact email
    billing_user = organization.owner

    customer = stripe.Customer.create(
        email=billing_user.email,
        name=organization.name,
        metadata={'organization_id': organization.id}
    )

    org_meta.stripe_customer_id = customer.id
    org_meta.save()
    return customer.id


def subscribe(request: HttpRequest, price_id: str, organization: Organization, quantity: int) -> HttpResponse:
    if get_active_subscription(organization) is not None:
        messages.error(request, f"The organization ({organization.name}) is already subscribed. "
                                f"Manage subscriptions in Settings > Organization.")
        # Ensure 'redirect_if_referer_not_found' is replaced with a real URL name
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings')))

    try:
        customer_id = create_org_customer_if_needed(organization)
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,  # Use the Organization's Stripe Customer ID
            success_url=ROOT_DOMAIN + '/checkout-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=ROOT_DOMAIN + '/checkout-cancelled',
            # payment_method_types=['card'],
            automatic_tax={
                "enabled": True,
            },
            customer_update={
                'address': 'auto'
            },
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': quantity
            }],
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, str(e))
        logger.error(f"Stripe Checkout Error: {e}", exc_info=True)
        return HttpResponseRedirect(reverse('bom:settings'))


def manage_subscription(request: HttpRequest, organization: Organization) -> HttpResponse:
    if get_active_subscription(organization) is None:
        messages.error(request, f"The organization ({organization.name}) is not yet subscribed.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings')))

    try:
        org_meta = get_organization_meta_or_404(organization)
        customer_id = org_meta.stripe_customer_id
        session = stripe.billing_portal.Session.create(
            customer=customer_id,  # Use the Organization's Stripe Customer ID
            return_url=ROOT_DOMAIN + reverse('bom:settings'),
        )
        return redirect(session.url, code=303)
    except Exception as e:
        logger.error(f"Error creating Stripe Billing Portal session: {e}", exc_info=True)
        messages.error(request, "Error creating stripe session, please try again or contact support.")
        return HttpResponseRedirect(reverse('bom:settings'))


# --- Webhook Handlers ---

# Note: This requires the @csrf_exempt decorator in the URL configuration,
# but it is omitted here as it belongs in views.py or urls.py.
def subscription_changed_handler(event: stripe.Event):
    data = event.get('data', {}).get('object')

    try:
        org_meta = OrganizationMeta.objects.get(stripe_customer_id=data.get('customer'))
        organization = org_meta.organization
    except OrganizationMeta.DoesNotExist:
        logger.warning(f"Webhook received for unknown customer ID: {data.get('customer')}")
        return

    subscription_id = data.get('id')
    status = data.get('status')

    quantity = data.get('quantity', 1)
    prices = data.get('items', {}).get('data', [])
    if len(prices) == 0:
        logger.error(f"Subscription changed event for {organization.name} ({organization.id}) has no prices.")
        return
    price = prices[0]
    price_id = price.get('price', {}).get('id')

    sub_obj, created = OrganizationSubscription.objects.update_or_create(
        stripe_subscription_id=subscription_id,
        defaults={
            "organization_meta": org_meta,
            "stripe_price_id": price_id,
            "status": status,
            "quantity": quantity,
            "current_period_start": _to_dt(data.get("current_period_start")),
            "current_period_end": _to_dt(data.get("current_period_end")),
        },
    )
    if created and not sub_obj.started_by:
        sub_obj.started_by = org_meta.organization.owner
        sub_obj.save(update_fields=["started_by"])

    if status == 'active':
        organization.subscription = SUBSCRIPTION_TYPE_PRO
        organization.subscription_quantity = quantity
        logger.info(f"Updated subscription for organization {organization.name} to PRO ({quantity} users)")
    else:
        organization.subscription = SUBSCRIPTION_TYPE_FREE
        organization.subscription_quantity = 1
        logger.info(f"Subscription status for {organization.name} changed to {status}. Set to FREE.")

    organization.save()


def subscription_issue_handler(event: stripe.Event):
    data = event.get('data', {}).get('object')

    try:
        org_meta = OrganizationMeta.objects.get(stripe_customer_id=data.get('customer'))
        organization = org_meta.organization

        email = organization.owner.email  # Assuming the organization model has a primary contact email
        send_mail(
            'IndaBOM Payment Failed',
            'Just writing to give you a heads up that your payment has failed and your subscription has been marked to be suspended. Please visit IndaBOM and update your payment settings.',
            'no-reply@indabom.com',
            [email, ],
            fail_silently=False,
        )
    except OrganizationMeta.DoesNotExist:
        logger.warning(f"Invoice failed for unknown customer ID: {data.get('customer')}")
    except Exception as err:
        logger.error(f'Error sending subscription issue email for event ({event.id}): {str(err)}', exc_info=True)


def stripe_webhook(request: HttpRequest) -> HttpResponse:
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        # Let 'customer.subscription.created' or 'customer.subscription.updated' handle the creation/status change
        pass

    elif event['type'] == 'customer.subscription.updated' or event['type'] == 'customer.subscription.created':
        transaction.on_commit(lambda: subscription_changed_handler(event))

    elif event['type'] == 'invoice.payment_failed':
        transaction.on_commit(lambda: subscription_issue_handler(event))

    elif event['type'] == 'invoice.paid':
        # Often handled by subscription.updated, but you can add custom logic here if needed
        pass

    return HttpResponse(status=200)
