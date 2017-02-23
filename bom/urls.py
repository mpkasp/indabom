from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^(?P<part_id>[0-9]+)/$', views.export_part_indented, name='export-part-indented'),
]