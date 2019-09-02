from django.conf.urls import include, url
from django.urls import path
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.contrib import admin
from django.conf import settings
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

from .sitemaps import StaticViewSitemap
from . import views

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

    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    path('learn-more/', TemplateView.as_view(template_name='learn-more.html'), name='learn-more'),
    path('privacy-policy/', TemplateView.as_view(template_name='privacy-policy.html'), name='privacy-policy'),
    path('install/', TemplateView.as_view(template_name='install.html'), name='install'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type="text/plain"), name="robots-file"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
