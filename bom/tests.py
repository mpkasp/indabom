from django.test import TestCase

#TODO: need to actually make some tests...

class TestOctopart():
    def test_match_part():
        p1 = create_some_fake_parts()
        p1.save()
        a = match_part(p1)