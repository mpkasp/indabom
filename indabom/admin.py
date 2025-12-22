from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import (
    OrganizationMeta,
    OrganizationSubscription,
    CheckoutSessionRecord,
    EmailTemplate,
    EmailSendLog,
)

User = get_user_model()


@admin.register(OrganizationMeta)
class OrganizationMetaAdmin(admin.ModelAdmin):
    list_display = ('organization', 'stripe_customer_id',)
    raw_id_fields = ('organization',)
    ordering = ('organization__name',)


class CheckoutSessionRecordInline(admin.TabularInline):
    model = CheckoutSessionRecord
    fk_name = 'organization_subscription'
    raw_id_fields = ('organization_subscription',)


@admin.register(OrganizationSubscription)
class OrganizationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('organization_meta', 'quantity', 'started_by', 'status')
    inlines = [CheckoutSessionRecordInline]
    raw_id_fields = ('organization_meta', 'started_by',)


@admin.register(CheckoutSessionRecord)
class CheckoutSessionRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization_subscription', 'renewal_consent_timestamp')
    raw_id_fields = ('user', 'organization_subscription',)
    ordering = ('-renewal_consent_timestamp',)

class EmailSendLogInline(admin.TabularInline):
    model = EmailSendLog
    extra = 0
    readonly_fields = ("email", "status", "message_id", "error", "sent_at", "user")


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "enabled", "updated_at", "last_sent_at")
    search_fields = ("name", "subject")
    inlines = [EmailSendLogInline]


@admin.register(EmailSendLog)
class EmailSendLogAdmin(admin.ModelAdmin):
    list_display = ("template", "email", "status", "message_id", "sent_at")
    list_filter = ("status", "template")
    search_fields = ("email", "message_id")
    readonly_fields = ("template", "user", "email", "status", "message_id", "error", "sent_at")

# Try to unregister User model
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

admin.site.register(User, UserAdmin)
