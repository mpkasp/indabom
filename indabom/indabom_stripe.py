from django.http import JsonResponse
from django.contrib.auth import get_user_model
from indabom.settings import STRIPE_TEST_SECRET_KEY

from djstripe.models import Product
import stripe, djstripe

User = get_user_model()


def subscribe(price_id: str, user: User) -> JsonResponse:
    stripe.api_key = STRIPE_TEST_SECRET_KEY

    try:
        customer = stripe.Customer.create(
            # payment_method=payment_method,
            email=user.email,
            invoice_settings={
                # 'default_payment_method': payment_method
            }
        )

        djstripe_customer = djstripe.models.Customer.sync_from_stripe_data(customer)

        # At this point, associate the ID of the Customer object with your
        # own internal representation of a customer, if you have one.
        user.customer = djstripe_customer

        # Subscribe the user to the subscription created
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": price_id, }, ],
            expand=["latest_invoice.payment_intent"]
        )

        djstripe_subscription = djstripe.models.Subscription.sync_from_stripe_data(subscription)

        user.subscription = djstripe_subscription
        user.save()
        return JsonResponse(subscription)
    except Exception as e:
        return JsonResponse({'error': (e.args[0])}, status=403)

    # Create Stripe Checkout session
    # checkout_session = stripe.checkout.Session.create(
    #     payment_method_types=["card"],
    #     mode="subscription",
    #     line_items=[
    #         {
    #             "price": price_id,
    #             "quantity": 1
    #         }
    #     ],
    #     customer=customer.id,
    #     success_url=f"https://YOURDOMAIN.com/payment/success?sessid={{CHECKOUT_SESSION_ID}}",
    #     cancel_url=f"https://YOURDOMAIN.com/payment/cancel",  # The cancel_url is typically set to the original product page
    # )
    # return JsonResponse({'sessionId': checkout_session.id})
    # return HttpResponseRedirect('/success/')


def add_user():
    pass


def unsubscribe():
    pass
