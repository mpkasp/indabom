from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^error/$', views.error, name='error'),
    url(r'^signup/$', views.bom_signup, name='signup'),
    url(r'^export/$', views.export_part_list, name='export-part-list'),
    url(r'^create-part/$', views.create_part, name='create-part'),
    url(r'^part/(?P<part_id>[0-9]+)/$', views.part_info, name='part-info'),
    url(r'^part/(?P<part_id>[0-9]+)/export/$', views.export_part_indented, name='export-part-indented'),
    url(r'^part/(?P<part_id>[0-9]+)/upload/$', views.upload_part_indented, name='upload-part-indented'),
    url(r'^part/(?P<part_id>[0-9]+)/part-match/$', views.octopart_part_match, name='octopart-part-match'),
    url(r'^part/(?P<part_id>[0-9]+)/part-match-indented/$', views.octopart_part_match_indented, name='octopart-part-match-indented'),
    url(r'^part/(?P<part_id>[0-9]+)/edit/$', views.edit_part, name='edit-part'),
    url(r'^part/(?P<part_id>[0-9]+)/delete/$', views.delete_part, name='delete-part'),
    url(r'^part/(?P<part_id>[0-9]+)/add-subpart/$', views.add_subpart, name='add-subpart'),
    url(r'^part/(?P<part_id>[0-9]+)/upload-file/$', views.upload_file_to_part, name='upload-file-to-part'),
    url(r'^part/(?P<part_id>[0-9]+)/remove-all-subparts/$', views.remove_all_subparts, name='remove-all-subparts'),
    url(r'^subpart/(?P<subpart_id>[0-9]+)/remove-subpart/$', views.remove_subpart, name='remove-subpart'),
    url(r'^partfile/(?P<partfile_id>[0-9]+)/delete-file/$', views.delete_file_from_part, name='delete-file-from-part'),
]
