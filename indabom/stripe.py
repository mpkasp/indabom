import logging
from typing import Optional

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse

import stripe
from djstripe import webhooks
from djstripe.models import Customer, Subscription
from sentry_sdk import capture_message

from bom.constants import SUBSCRIPTION_TYPE_FREE, SUBSCRIPTION_TYPE_PRO
from bom.models import Organization
from indabom.settings import ROOT_DOMAIN, STRIPE_SECRET_KEY


logger = logging.getLogger(__name__)
stripe.api_key = STRIPE_SECRET_KEY
User = get_user_model()

def active_subscription(customer: Customer) -> Optional[Subscription]:
    active_subscriptions = customer.active_subscriptions
    if len(active_subscriptions) > 1:
        raise ValueError(f'Too many subscriptions found for user, {len(active_subscriptions)} is greater than 1.')
    elif len(active_subscriptions) == 1:
        return active_subscriptions[0]
    return None

def subscription_changed(event, **kwargs):
    try:
        customer = event.customer
        organization = customer.subscriber
        subscription = active_subscription(customer)
    except (AttributeError, ValueError) as err:
        error_msg = f'Subscription Changed Error - {str(err)}'
        capture_message(error_msg)
        logger.warning(error_msg)
        return

    if subscription is not None:
        organization.subscription = SUBSCRIPTION_TYPE_PRO
        organization.subscription_quantity = subscription.quantity
    else:
        organization.subscription = SUBSCRIPTION_TYPE_FREE
        organization.subscription_quantity = 1
    organization.save()
    logger.info(f"Updated subscription for organization {organization.name} ({organization.id}) to {organization.subscription} ({subscription.quantity} users)")

@webhooks.handler("invoice", "customer.subscription")
def subscription_changed_handler(event, **kwargs):
    transaction.on_commit(lambda: subscription_changed(event, **kwargs))

@webhooks.handler("invoice.payment_failed")
def subscription_issue_handler(event, **kwargs):
    customer = event.customer
    organization = customer.subscriber
    email = organization.email
    send_mail(
        'IndaBOM Payment Failed',
        'Just writing to give you a heads up that your payment has failed and your subscription has been marked to be suspended. Please visit IndaBOM and update your payment settings.',
        'no-reply@indabom.com',
        [email, ],
        fail_silently=False,
    )

def subscribe(request: HttpRequest, price_id: str, organization: Organization, quantity: int) -> HttpResponse:
    customer, _ = Customer.get_or_create(subscriber=organization)

    if active_subscription(customer) is not None:
        messages.error(request, f"The organization ({organization.name}) is already subscribed. Manage subscriptions in Settings > Organization.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))

    try:
        # https://stripe.com/docs/api/checkout/sessions/create
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            # {CHECKOUT_SESSION_ID} is a string literal; do not change it!
            success_url=ROOT_DOMAIN + '/checkout-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=ROOT_DOMAIN + '/checkout-cancelled',
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': price_id,
                'quantity': quantity
            }],
        )

        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings')))


def manage_subscription(request: HttpRequest, organization: Organization) -> HttpResponse:
    customer, _ = Customer.get_or_create(subscriber=organization)

    if active_subscription(customer) is None:
        messages.error(request, f"The organization ({organization.name}) is not yet subscribed.")
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings')))

    try:
        # https://stripe.com/docs/billing/subscriptions/integrating-customer-portal
        session = stripe.billing_portal.Session.create(
            customer=customer.id,
            return_url=ROOT_DOMAIN + reverse('bom:settings'),
        )

        return redirect(session.url, code=303)
    except Exception as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings')))
