from bom.models import Organization
from django.conf import settings
from django.contrib.auth.models import AbstractUser, User
from django.db import models


class OrganizationMeta(models.Model):
    organization = models.OneToOneField(Organization, db_index=True, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True, unique=True)

    def _organization_meta(self):
        return OrganizationMeta.objects.get_or_create(organization=self)[0]

    Organization.add_to_class('meta', _organization_meta)

    @property
    def active_subscription(self):
        try:
            return self.organizationsubscription_set.get(status='active')
        except OrganizationSubscription.DoesNotExist:
            return None
        except OrganizationSubscription.MultipleObjectsReturned:
            print("WARNING: Multiple active subscriptions found!")
            return self.organizationsubscription_set.filter(status='active').first()

    def active_user_count(self):
        subscription = self.active_subscription
        if not subscription:
            return 1
        return subscription.quantity


class OrganizationSubscription(models.Model):
    organization_meta = models.ForeignKey(OrganizationMeta, on_delete=models.CASCADE)
    stripe_subscription_id = models.CharField(max_length=50, unique=True, db_index=True)
    stripe_price_id = models.CharField(max_length=50)
    status = models.CharField(max_length=20, default='incomplete')  # e.g., 'active', 'canceled', 'incomplete'
    quantity = models.IntegerField(default=1)  # The number of allowed users/seats
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.organization_meta.organization.name} - {self.status}"


class CheckoutSessionRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    renewal_consent = models.BooleanField(default=False)
    renewal_consent_timestamp = models.DateTimeField(null=True)
    renewal_consent_text = models.TextField(null=True, blank=True)
    checkout_session_id = models.CharField(max_length=50)
    stripe_subscription_id = models.CharField(max_length=50)
    organization_subscription = models.ForeignKey(OrganizationSubscription, null=True, default=None,
                                                  on_delete=models.CASCADE)
