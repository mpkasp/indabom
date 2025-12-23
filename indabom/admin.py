from bom.models import Organization as BomOrganization
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    OrganizationMeta,
    OrganizationSubscription,
    CheckoutSessionRecord,
    EmailTemplate,
    EmailSendLog,
    IndabomUserMeta,
)
from .settings import STRIPE_SECRET_KEY
from .stripe import manage_subscription as stripe_manage_subscription

User = get_user_model()


class OrganizationSubscriptionInline(admin.TabularInline):
    model = OrganizationSubscription
    fk_name = 'organization_meta'
    raw_id_fields = ('organization_meta', 'started_by',)
    readonly_fields = ('stripe_subscription_id', 'stripe_price_id', 'current_period_start', 'current_period_end',
                       'status', 'quantity', 'started_by')
    extra = 0
    max_num = 0


class CheckoutSessionRecordInline(admin.TabularInline):
    model = CheckoutSessionRecord
    fk_name = 'organization_subscription'
    raw_id_fields = ('organization_subscription',)


class EmailSendLogInline(admin.TabularInline):
    model = EmailSendLog
    extra = 0
    readonly_fields = ("email", "status", "message_id", "error", "sent_at", "user")


class IndabomUserMetaInline(admin.TabularInline):
    model = IndabomUserMeta
    readonly_fields = ("terms_accepted_at",)
    can_delete = False


class BomOrganizationInline(admin.TabularInline):
    model = BomOrganization
    fk_name = 'owner'
    raw_id_fields = ('owner',)

@admin.register(OrganizationMeta)
class OrganizationMetaAdmin(admin.ModelAdmin):
    list_display = ('organization', 'stripe_customer_id',)
    raw_id_fields = ('organization',)
    ordering = ('organization__name',)
    inlines = [OrganizationSubscriptionInline]
    readonly_fields = ("stripe_portal_link", "stripe_customer_link",)
    fieldsets = (
        (None, {
            'fields': ('organization', 'stripe_customer_id', 'stripe_portal_link', 'stripe_customer_link')
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/manage-subscription/',
                self.admin_site.admin_view(self.manage_subscription_view),
                name='indabom_organizationmeta_manage_subscription',
            ),
        ]
        return custom_urls + urls

    def stripe_portal_link(self, obj: OrganizationMeta):
        if not obj or not obj.stripe_customer_id:
            return ""
        url = reverse('admin:indabom_organizationmeta_manage_subscription', args=[obj.pk])
        return format_html('<a class="button" href="{}">Open Stripe billing portal</a>', url)

    stripe_portal_link.short_description = "Stripe billing portal"

    def stripe_customer_link(self, obj: OrganizationMeta):
        if not obj or not obj.stripe_customer_id:
            return ""
        base = "https://dashboard.stripe.com"
        # Heuristic: test keys start with sk_test_
        if STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith("sk_test_"):
            base += "/test"
        cust_url = f"{base}/customers/{obj.stripe_customer_id}"
        return format_html('<a class="button" target="_blank" rel="noopener" href="{}">Open Stripe customer</a>',
                           cust_url)

    stripe_customer_link.short_description = "Stripe customer (dashboard)"

    def manage_subscription_view(self, request, pk: int):
        obj = OrganizationMeta.objects.get(pk=pk)
        # Re-use existing portal creation/redirect logic
        return stripe_manage_subscription(request, obj.organization)


@admin.register(OrganizationSubscription)
class OrganizationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('organization_meta__organization', 'quantity', 'started_by', 'status')
    inlines = [CheckoutSessionRecordInline]
    raw_id_fields = ('organization_meta', 'started_by',)
    readonly_fields = ('stripe_subscription_id', 'stripe_price_id', 'current_period_start', 'current_period_end',
                       'status', 'quantity')


@admin.register(CheckoutSessionRecord)
class CheckoutSessionRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization_subscription', 'renewal_consent_timestamp')
    raw_id_fields = ('user', 'organization_subscription',)
    ordering = ('-renewal_consent_timestamp',)


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


current_admin = admin.site._registry.get(User)

if current_admin:
    admin_class = current_admin.__class__
    inlines = list(admin_class.inlines or [])
    if IndabomUserMetaInline not in inlines:
        inlines.append(IndabomUserMetaInline)
        admin_class.inlines = inlines
else:
    class IndabomUserAdmin(UserAdmin):
        inlines = [IndabomUserMetaInline]


    admin.site.register(User, IndabomUserAdmin)
