from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.views.generic import TemplateView

from . import views
from .sitemaps import StaticViewSitemap

# Dictionary containing your sitemap classes
sitemaps = {
    'static': StaticViewSitemap(),
}

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('', views.index, name='index'),
    path('bom/', include('bom.urls')),
    path('signup/', views.signup, name='signup'),

    path('admin/', admin.site.urls, name='admin'),
    path('login/', auth_views.LoginView.as_view(
        template_name='indabom/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='indabom/password-reset.html',
                                                                 from_email='no-reply@indabom.com',
                                                                 subject_template_name='indabom/password-reset-subject.txt',
                                                                 email_template_name='indabom/password-reset-email.html'),
         name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='indabom/password-reset-done.html'),
         name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='indabom/password-reset-confirm.html'),
         name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='indabom/password-reset-complete.html'), name='password_reset_complete'),

    path('about/', views.About.as_view(), name=views.About.name),
    path('product/', views.Product.as_view(), name=views.Product.name),
    path('privacy-policy/', views.PrivacyPolicy.as_view(), name=views.PrivacyPolicy.name),
    path('terms-and-conditions/', views.TermsAndConditions.as_view(), name=views.TermsAndConditions.name),
    path('update-terms/', views.update_terms, name='update-terms'),
    path('install/', views.Install.as_view(), name=views.Install.name),
    path('pricing/', views.Pricing.as_view(), name=views.Pricing.name),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type="text/plain"), name="robots-file"),

    path('checkout/', login_required(views.Checkout.as_view()), name=views.Checkout.name),
    path('checkout-success/', views.CheckoutSuccess.as_view(), name=views.CheckoutSuccess.name),
    path('checkout-cancelled/', views.CheckoutCancelled.as_view(), name=views.CheckoutCancelled.name),
    path('stripe-manage/', views.stripe_manage, name='stripe-manage'),
    path('webhooks/stripe/', views.stripe_webhook, name='stripe-webhook'),
    path('account/delete/', views.delete_account, name='account-delete'),

    path('explorer/', include('explorer.urls')),
    path('sentry-debug/', trigger_error)
]

handler404 = 'indabom.views.handler404'
handler500 = 'indabom.views.handler500'

if settings.DEBUG:
    media_url_prefix = settings.MEDIA_URL if settings.MEDIA_URL else '/media/'
    urlpatterns += static(media_url_prefix, document_root=settings.MEDIA_ROOT)
