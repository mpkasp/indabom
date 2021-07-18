from django.contrib.auth.models import AbstractUser, User
from django.db import models

from djstripe.models import Customer, Subscription

from bom.models import Organization
from indabom.settings import INDABOM_STRIPE_PRICE_ID


# class OrganizationMeta(models.Model):
#     organization = models.OneToOneField(Organization, db_index=True, on_delete=models.CASCADE)
#
#     def _organization_meta(self):
#         return OrganizationMeta.objects.get_or_create(organization=self)[0]
#
#     @property
#     def customer(self):
#         return Customer.objects.get(subscriber=self)
#
#     @property
#     def active_subscriptions(self):
#         return self.customer.active_subscriptions()
#
#     def active_user_count(self):
#         active_subscriptions = self.active_subscriptions
#         if active_subscriptions > 1:
#             raise ValueError('Too many subscriptions found for user.')
#         elif active_subscriptions <= 0:
#             return 1
#
#         return self.active_subscriptions[0].quantity
#
#     Organization.add_to_class('meta', _organization_meta)