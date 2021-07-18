from urllib.error import URLError

from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import get_object_or_404, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

import stripe
from djstripe.models import Price

from bom.models import Organization
from indabom import stripe
from indabom.forms import OrganizationForm, SubscriptionForm, UserForm
from indabom.settings import DEBUG, INDABOM_STRIPE_PRICE_ID


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
    form_class = SubscriptionForm

    def get_context_data(self, *args, **kwargs):
        context = super(Checkout, self).get_context_data(**kwargs)
        price = Price.objects.filter(id=INDABOM_STRIPE_PRICE_ID).first()

        human_readable_prices = []
        for tier in price.tiers:
            up_to = tier['up_to']
            flat_amount = tier['flat_amount']
            unit_amount = tier['unit_amount']
            if flat_amount and up_to:
                human_readable_prices.append(f'${flat_amount / 100:.2f} for up to {up_to} users')
            elif unit_amount:
                human_readable_prices.append(f'${unit_amount / 100:.2f} per user')

        form = self.form_class(initial={'price_id': price.id}, owner=self.request.user)
        del form.fields["additional_users"]

        context.update({
            'price': price,
            'product': price.product,
            'form': form,
            'human_readable_prices': human_readable_prices,
        })
        return context

    @login_required
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())

    @login_required
    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, owner=request.user)

        if form.is_valid():
            organization = form.cleaned_data['organization']
            price_id = form.cleaned_data['price_id']
            quantity = form.cleaned_data['additional_users'] + 5
            return stripe.subscribe(request, price_id, organization, quantity)

        del form.fields["additional_users"]
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class CheckoutSuccess(IndabomTemplateView):
    name = 'checkout-success'


class CheckoutCancelled(IndabomTemplateView):
    name = 'checkout-cancelled'


@login_required
def stripe_manage(request):
    user_profile = request.user.bom_profile()
    organization = user_profile.organization
    if user_profile.is_organization_owner():
        return stripe.manage_subscription(request, organization)

    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings') + '#organization'))
