from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect

import stripe
from djstripe.models import Customer, Price, Product, Subscription

from bom.models import Organization
from indabom.settings import STRIPE_SECRET_KEY


User = get_user_model()


def subscribe(request: HttpRequest, price_id: str, organization: Organization) -> HttpResponse:
    stripe.api_key = STRIPE_SECRET_KEY
    customer, _ = Customer.get_or_create(subscriber=organization)

    try:
        # https://stripe.com/docs/api/checkout/sessions/create
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            # {CHECKOUT_SESSION_ID} is a string literal; do not change it!
            success_url='https://indabom.com/success.html?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://indabom.com/canceled.html',
            payment_method_types=['card'],
            mode='subscription',
            line_items=[{
                'price': price_id,
                # For metered billing, do not pass quantity
                'quantity': 1
            }],
        )

        # Sync the Stripe API return data to the database,
        # this way we don't need to wait for a webhook-triggered sync
        subscription = Subscription.sync_from_stripe_data(checkout_session)
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        messages.error(request, str(e))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))


def add_user():
    pass


def unsubscribe():
    pass
