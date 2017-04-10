from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^(?P<part_id>[0-9]+)/$', views.part_info, name='part-info'),
    url(r'^(?P<part_id>[0-9]+)/(?P<qty>[0-9]+)/$', views.part_info, name='part-info'),
    url(r'^(?P<part_id>[0-9]+)/export/$', views.export_part_indented, name='export-part-indented'),
    url(r'^(?P<part_id>[0-9]+)/upload/$', views.upload_part_indented, name='upload-part-indented'),
    url(r'^(?P<part_id>[0-9]+)/part_match/$', views.octopart_part_match, name='octopart-part-match'),
    url(r'^(?P<part_id>[0-9]+)/part_match_indented/$', views.octopart_part_match_indented, name='octopart-part-match-indented'),
    url(r'^export/$', views.export_part_list, name='export-part-list'),
]
