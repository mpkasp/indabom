import logging
from datetime import datetime
from typing import Optional
from urllib.error import URLError

from bom.models import Organization, UserMeta
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpResponseNotFound,
    HttpResponseRedirect,
    HttpResponseServerError,
    HttpResponse,
)
from django.shortcuts import render, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import TemplateView

from indabom import stripe
from indabom.forms import SubscriptionForm, UserForm, PasswordConfirmForm
from indabom.models import CheckoutSessionRecord, IndabomUserMeta
from indabom.settings import DEBUG, INDABOM_STRIPE_PRICE_ID, NEW_TERMS_EFFECTIVE

logger = logging.getLogger(__name__)

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


class Product(IndabomTemplateView):
    name = 'product'


class PrivacyPolicy(IndabomTemplateView):
    name = 'privacy-policy'

    def get_context_data(self, *args, **kwargs):
        context = super(PrivacyPolicy, self).get_context_data(**kwargs)
        context['new_terms_effective'] = NEW_TERMS_EFFECTIVE
        return context


class TermsAndConditions(IndabomTemplateView):
    name = 'terms-and-conditions'

    def get_context_data(self, *args, **kwargs):
        context = super(TermsAndConditions, self).get_context_data(**kwargs)
        context['new_terms_effective'] = NEW_TERMS_EFFECTIVE
        return context


class Install(IndabomTemplateView):
    name = 'install'


class Pricing(IndabomTemplateView):
    name = 'pricing'


class Checkout(IndabomTemplateView):
    name = 'checkout'
    initial = {}
    form_class = SubscriptionForm
    user_profile: Optional[UserMeta] = None
    organization: Optional[Organization] = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.user_profile = request.user.bom_profile()
        self.organization = self.user_profile.organization

    def get_context_data(self, *args, **kwargs):
        context = super(Checkout, self).get_context_data(**kwargs)
        form = self.form_class(owner=self.request.user)
        del form.fields["unit"]

        stripe_price = stripe.get_price(INDABOM_STRIPE_PRICE_ID, self.request)

        context.update({
            'organization': self.organization,
            'user_profile': self.user_profile,
            'price': stripe_price,
            'form': form,
            'product': None,
        })

        if stripe_price is None:
            return context

        context.update({'human_readable_price': stripe_price.unit_amount / 100})

        stripe_product = stripe.get_product(stripe_price.product, self.request)
        if stripe_product is None:
            return context

        context.update({'product': stripe_product})
        form.initial = {'price_id': INDABOM_STRIPE_PRICE_ID}

        return context

    def get(self, request, *args, **kwargs):
        user_profile = self.user_profile
        organization: Optional[Organization] = self.organization

        if not user_profile.is_organization_owner():
            if organization is not None and organization.owner is not None:
                messages.error(request,
                               f'Only your organization owner {organization.owner.email} can upgrade the organization.')
            else:
                messages.error(request, f'You must be an organization owner to upgrade your organization.')
            return HttpResponseRedirect(reverse('bom:settings'))

        try:
            if stripe.get_active_subscription(organization) is not None:
                messages.info(request, "You already have an active subscription.")
                return HttpResponseRedirect(reverse('stripe-manage'))
        except Exception:  # Catch any exceptions from database lookup
            messages.error(request,
                           f'There was an error getting your organization. Please contact info@indabom.com with this error message.')
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings') + '#organization'))

        return render(request, self.template_name, self.get_context_data())

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, owner=request.user)

        if form.is_valid():
            organization = form.cleaned_data['organization']
            price_id = form.cleaned_data['price_id']
            quantity = form.cleaned_data['unit']
            checkout_session_record = CheckoutSessionRecord.objects.create(
                user=request.user,
                renewal_consent=form.cleaned_data['renewal_consent'],
                renewal_consent_text=form.renewal_consent_text,
                renewal_consent_timestamp=datetime.now(),
            )

            checkout_session = stripe.subscribe(request, price_id, organization, quantity, checkout_session_record)
            if checkout_session is None:
                return HttpResponseRedirect(reverse('bom:settings'))
            checkout_session_record.checkout_session_id = checkout_session.id
            checkout_session_record.save()
            response = redirect(checkout_session.url)
            response.status_code = 303
            return response

        if "unit" in form.fields:
            del form.fields["unit"]

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

    if user_profile.is_organization_owner() and organization is not None:
        return stripe.manage_subscription(request, organization)

    messages.warning(request, "Can't manage a subscription for an organization you don't own.")
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('bom:settings') + '#organization'))


@login_required
def delete_account(request):
    user = request.user
    user_profile = user.bom_profile()
    organization = user_profile.organization

    # Determine owner and subscription status
    is_owner = user_profile.is_organization_owner()
    has_active_sub = False
    if is_owner and organization is not None:
        try:
            has_active_sub = stripe.get_active_subscription(organization) is not None
        except Exception:
            messages.error(request,
                           'There was an error checking your subscription. Please contact support at info@indabom.com.')
            return HttpResponseRedirect(reverse('bom:settings') + '#organization')

    # Block owners with active subscription
    if is_owner and has_active_sub:
        messages.error(request, 'You have an active subscription. Please cancel it first. Redirecting you to manage your subscription.')
        return HttpResponseRedirect(reverse('stripe-manage'))

    if request.method == 'POST':
        form = PasswordConfirmForm(request.POST, user=user)
        if form.is_valid():
            # If owner (and not actively subscribed), delete their organization first
            if is_owner and organization is not None:
                org_name = organization.name
                organization.delete()
                messages.info(request, f'Organization "{org_name}" was deleted as part of account deletion.')

            # Delete the user and logout
            username = user.username
            user.delete()
            logout(request)
            return TemplateResponse(request, 'indabom/account-deleted.html', {'username': username})
        else:
            messages.error(request, 'Incorrect password, please try again.')
    else:
        form = PasswordConfirmForm(user=user)

    context = {
        'form': form,
        'is_owner': is_owner,
        'organization': organization,
        'has_active_sub': has_active_sub,
    }
    return TemplateResponse(request, 'indabom/delete-account.html', context)


@csrf_exempt
def stripe_webhook(request):
    # Check if the request method is POST, which is required for webhooks
    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    try:
        return stripe.stripe_webhook(request)
    except Exception as e:
        logger.error(f"Failed to process Stripe webhook: {e}", exc_info=True)
        return HttpResponse('Webhook failed to process.', status=500)


@login_required
def update_terms(request):
    if request.method == 'POST':
        next_url = request.POST.get('next') or reverse('bom:home')
        settings_obj, _ = IndabomUserMeta.objects.get_or_create(user=request.user)
        settings_obj.terms_accepted_at = timezone.now()
        settings_obj.save()
        return redirect(next_url)

    next_url = request.GET.get('next') or reverse('bom:home')
    context = {
        'next': next_url,
        'new_terms_effective': NEW_TERMS_EFFECTIVE,
    }
    return TemplateResponse(request, 'indabom/update-terms.html', context)
