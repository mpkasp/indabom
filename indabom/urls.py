from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.sitemaps.views import sitemap
from django.urls import path
from django.views.generic import TemplateView

from . import views
from .sitemaps import StaticViewSitemap


# Dictionary containing your sitemap classes
sitemaps = {
    'static': StaticViewSitemap(),
}

urlpatterns = [
    path('', views.index, name='index'),
    path('bom/', include('bom.urls')),
    path('signup/', views.signup, name='signup'),

    path('admin/', admin.site.urls, name='admin'),
    path('login/', auth_views.LoginView.as_view(template_name='indabom/login.html'),
         {'redirect_authenticated_user': True}, name='login'),
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
    path('learn-more/', views.LearnMore.as_view(), name=views.LearnMore.name),
    path('privacy-policy/', views.PrivacyPolicy.as_view(), name=views.PrivacyPolicy.name),
    path('terms-and-conditions/', views.TermsAndConditions.as_view(), name=views.TermsAndConditions.name),
    path('install/', views.Install.as_view(), name=views.Install.name),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type="text/plain"), name="robots-file"),

    path('stripe/', include('djstripe.urls', namespace='djstripe')),
    path('checkout/', login_required(views.Checkout.as_view()), name=views.Checkout.name),
    path('checkout-success/', views.CheckoutSuccess.as_view(), name=views.CheckoutSuccess.name),
    path('checkout-cancelled/', views.CheckoutCancelled.as_view(), name=views.CheckoutCancelled.name),
    path('stripe-manage/', views.stripe_manage, name='stripe-manage'),
]

handler404 = 'indabom.views.handler404'
handler500 = 'indabom.views.handler500'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
