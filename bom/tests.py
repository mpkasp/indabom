from django.test import TestCase, Client
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from unittest import skip

from .helpers import create_some_fake_parts
from .octopart_parts_match import match_part

class TestBOM(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('kasper', 'kasper@friendlyghost.com', 'ghostpassword')

    @skip("only test when we want to hit octopart's api")
    def test_match_part(self):
        self.client.login(username='kasper', password='ghostpassword')

        (p1, p2, p3) = create_some_fake_parts()
        a = match_part(p1)

        partExists = len(a) > 0

        self.assertEqual(partExists, True)


    def test_part_info(self):
        self.client.login(username='kasper', password='ghostpassword')

        (p1, p2, p3) = create_some_fake_parts()

        response = self.client.post(reverse('part-info', kwargs={'part_id': p1.id}))
        self.assertEqual(response.status_code, 200)


    def test_export_part_indented(self):
        self.client.login(username='kasper', password='ghostpassword')

        (p1, p2, p3) = create_some_fake_parts()
        
        response = self.client.post(reverse('export-part-indented', kwargs={'part_id': p1.id}))
        self.assertEqual(response.status_code, 200)


    @skip("will need to grab a test csv at some point")
    def test_upload_part_indented(self):
        (p1, p2, p3) = create_some_fake_parts()
        
        response = self.client.post(reverse('upload-part-indented', kwargs={'part_id': p1.id}))
        self.assertEqual(response.status_code, 200)
