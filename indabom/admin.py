from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import (
    OrganizationMeta,
    OrganizationSubscription,
    CheckoutSessionRecord
)

User = get_user_model()


class OrganizationMetaAdmin(admin.ModelAdmin):
    list_display = ('organization', 'stripe_customer_id',)
    raw_id_fields = ('organization',)
    ordering = ('organization__name',)


class CheckoutSessionRecordInline(admin.TabularInline):
    model = CheckoutSessionRecord
    fk_name = 'organization_subscription'
    raw_id_fields = ('organization_subscription',)


class OrganizationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('organization_meta', 'quantity', 'started_by', 'status')
    inlines = [CheckoutSessionRecordInline]
    raw_id_fields = ('organization_meta', 'started_by',)


class CheckoutSessionRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization_subscription', 'renewal_consent_timestamp')
    raw_id_fields = ('user', 'organization_subscription',)
    ordering = ('-renewal_consent_timestamp',)

# Try to unregister User model
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)
admin.site.register(OrganizationMeta, OrganizationMetaAdmin)
admin.site.register(OrganizationSubscription, OrganizationSubscriptionAdmin)
admin.site.register(CheckoutSessionRecord, CheckoutSessionRecordAdmin)
