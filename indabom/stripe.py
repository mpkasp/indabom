from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect

import stripe
from djstripe.models import Customer

from bom.models import Organization
from indabom.settings import ROOT_DOMAIN, STRIPE_SECRET_KEY


User = get_user_model()

def subscribe(request: HttpRequest, price_id: str, organization: Organization, quantity: int) -> HttpResponse:
    stripe.api_key = STRIPE_SECRET_KEY
    customer, _ = Customer.get_or_create(subscriber=organization)

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
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))


def add_user():
    # TODO: Update existing subscription to increase qty
    pass


def unsubscribe():
    # TODO
    pass
