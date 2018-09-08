from django.conf.urls import include, url
from django.urls import path
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.contrib.sitemaps.views import sitemap
from django.contrib import admin
from django.conf import settings
from django.views.generic import TemplateView

from .sitemaps import StaticViewSitemap
from . import views

# Dictionary containing your sitemap classes
sitemaps = {
   'static': StaticViewSitemap(),
}

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^signup/', views.signup, name='signup'),
    url(r'^bom/', include('bom.urls'), name='bom'),

    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), {'template_name': 'indabom/login.html', 'redirect_authenticated_user': True}, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), {'next_page': '/'}, name='logout'),

    url(r'^about/$', TemplateView.as_view(template_name='about.html'), name='about'),
    url(r'^install/$', TemplateView.as_view(template_name='install.html'), name='install'),
    url(r'^sitemap\.xml$', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
