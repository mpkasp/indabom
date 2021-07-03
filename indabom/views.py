from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseNotFound, JsonResponse
from django.contrib.auth import authenticate, login, get_user_model
from django.contrib.auth.decorators import login_required
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.generic.base import TemplateView

from indabom.settings import DEBUG, STRIPE_TEST_SECRET_KEY
from indabom.forms import UserForm, StripeIdForm
from indabom.indabom_stripe import subscribe, add_user, unsubscribe

from urllib.error import URLError
from djstripe.models import Product
import stripe, djstripe


def index(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('bom:home'))
    else:
        return TemplateResponse(request, 'indabom/index.html', locals())


def handler404(request, exception=None, *args, **kwargs):
    return HttpResponseNotFound(render(request, 'indabom/404.html', status=404, context=locals()))


def handler500(request):
    return HttpResponseServerError(render(request, 'indabom/500.html', status=500))


def signup(request):
    name = 'signup'
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        try:
            if form.is_valid():
                new_user = form.save()
                login(request, new_user, backend='django.contrib.auth.backends.ModelBackend')
                return HttpResponseRedirect(reverse('bom:home'))
        except URLError:
            if DEBUG and len(form.errors.keys()) == 1 and 'captcha' in form.errors.keys():
                new_user = form.save()
                login(request, new_user, backend='django.contrib.auth.backends.ModelBackend')
                return HttpResponseRedirect(reverse('bom:home'))
    else:
        form = UserForm()

    return TemplateResponse(request, 'indabom/signup.html', locals())


class IndabomTemplateView(TemplateView):
    name = None

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.template_name = f'indabom/{self.name}.html'

    def get_context_data(self, *args, **kwargs):
        context = super(IndabomTemplateView, self).get_context_data(**kwargs)
        context['name'] = self.name
        return context


class About(IndabomTemplateView):
    name = 'about'


class LearnMore(IndabomTemplateView):
    name = 'learn-more'


class PrivacyPolicy(IndabomTemplateView):
    name = 'privacy-policy'


class TermsAndConditions(IndabomTemplateView):
    name = 'terms-and-conditions'


class Install(IndabomTemplateView):
    name = 'install'


class Checkout(IndabomTemplateView):
    name = 'checkout'
    initial = {}
    form_class = StripeIdForm
    products = Product.objects.all()
    # success_url = '/thanks/'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'products': self.products})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            # TODO: Make sure the customer is the owner of the organization ?
            customer = request.user
            price_id = form.cleaned_data['id']

            # TODO: subscribe to organization as customer?
            subscribe(price_id, customer)

        return render(request, self.template_name, {'form': form, 'products': self.products})


@login_required
def create_checkout_session(request):
    customer = request.user  # get customer model based off request.user

    if request.method == 'POST':
        # Assign product price_id, to support multiple products you
        # can include a product indicator in the incoming POST data
        price_id = ...  # get price.id from form
        stripe.api_key = STRIPE_TEST_SECRET_KEY

        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1
                }
            ],
            customer=customer.id,
            success_url=f"https://YOURDOMAIN.com/payment/success?sessid={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"https://YOURDOMAIN.com/payment/cancel",  # The cancel_url is typically set to the original product page
        )

    return JsonResponse({'sessionId': checkout_session.id})