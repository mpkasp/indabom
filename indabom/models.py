from bom.models import Organization
from django.conf import settings
from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.utils import timezone


class OrganizationMeta(models.Model):
    organization = models.OneToOneField(Organization, db_index=True, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=256, blank=True, null=True, unique=True)

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
    stripe_subscription_id = models.CharField(max_length=256, unique=True, db_index=True)
    stripe_price_id = models.CharField(max_length=256)
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
    checkout_session_id = models.CharField(max_length=256)
    stripe_subscription_id = models.CharField(max_length=256)
    organization_subscription = models.ForeignKey(OrganizationSubscription, null=True, default=None,
                                                  on_delete=models.CASCADE)


class EmailTemplate(models.Model):
    """A simple HTML email template to broadcast to users."""
    name = models.CharField(max_length=128, unique=True)
    subject = models.CharField(max_length=255)
    html_body = models.TextField(help_text="HTML content. You can use Django template variables like {{ user.first_name }}.")
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name


class EmailSendLog(models.Model):
    """Log of email sends per user and template for idempotency and rate limiting."""
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = (
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    )

    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, related_name='send_logs')
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    email = models.EmailField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES)
    message_id = models.CharField(max_length=256, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    sent_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["template", "email"]),
            models.Index(fields=["sent_at"]),
        ]

    def __str__(self):
        return f"{self.email} - {self.template.name} - {self.status}"


class IndabomUserMeta(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, db_index=True, on_delete=models.CASCADE,
                                related_name='indabom_meta')
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Settings for {self.user.username}"
