from typing import Iterable, Optional, List, Dict

from anymail.message import AnymailMessage
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from indabom.models import EmailTemplate, EmailSendLog


class Command(BaseCommand):
    help = "Send an EmailTemplate to users, respecting a daily cap and logging sends."

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--template-id', type=int, help='ID of the EmailTemplate to send')
        group.add_argument('--template-name', type=str, help='Name of the EmailTemplate to send')

        parser.add_argument('--from', dest='from_email', type=str, default=None,
                            help='Override from email (defaults to settings.DEFAULT_FROM_EMAIL)')
        parser.add_argument('--max-per-day', type=int, default=None,
                            help='Maximum emails to send today (defaults to settings.MAILGUN_DAILY_LIMIT)')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be sent without sending')
        parser.add_argument('--only-users', type=str, default=None,
                            help='Optional comma-separated list of email addresses to target')

    def handle(self, *args, **options):
        template = self._get_template(options)
        if not template.enabled:
            raise CommandError(f"EmailTemplate '{template}' is disabled. Enable it in admin to send.")

        from_email = options.get('from_email') or getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        if not from_email:
            raise CommandError('DEFAULT_FROM_EMAIL not set and no --from provided.')

        max_per_day = options.get('max_per_day') or getattr(settings, 'MAILGUN_DAILY_LIMIT', 80)
        dry_run = options.get('dry_run')

        target_emails: Optional[Iterable[str]] = None
        if options.get('only_users'):
            target_emails = [e.strip() for e in options['only_users'].split(',') if e.strip()]

        # compute remaining quota for today
        today = timezone.now().date()
        sent_today = EmailSendLog.objects.filter(sent_at__date=today).count()
        remaining_today = max(0, max_per_day - sent_today)

        if remaining_today <= 0:
            self.stdout.write(self.style.WARNING(
                f"Daily send limit reached ({max_per_day}). Nothing to send."))
            return

        User = get_user_model()
        users_qs = User.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email='')

        if target_emails is not None:
            users_qs = users_qs.filter(email__in=list(target_emails))

        # Exclude users already sent this template
        already_sent_emails = set(
            EmailSendLog.objects.filter(template=template, status=EmailSendLog.STATUS_SENT)
            .values_list('email', flat=True)
        )
        users_qs = users_qs.exclude(email__in=already_sent_emails)

        to_send = list(users_qs[:remaining_today])

        self.stdout.write(
            f"Template: {template.name} | Subject: {template.subject} | From: {from_email}\n"
            f"Daily cap: {max_per_day} | Already today: {sent_today} | Remaining today: {remaining_today}\n"
            f"Eligible recipients (after excluding already-sent): {len(to_send)}"
        )

        if not to_send:
            self.stdout.write(self.style.WARNING("No recipients to send."))
            return

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run: no emails sent."))
            for u in to_send:
                self.stdout.write(f"Would send to: {u.email}")
            return

        # Use django-anymail batch sending with Mailgun recipient variables
        # Convert any simple Django {{ user.* }} vars in subject/body to Mailgun %recipient.*% vars
        subject_template = self._convert_django_vars_to_mailgun(template.subject)
        html_template = self._convert_django_vars_to_mailgun(template.html_body)
        text_template = self._html_to_text(html_template)

        # Build recipient list and per-recipient merge data
        recipient_emails: List[str] = [u.email for u in to_send]
        merge_data: Dict[str, Dict[str, str]] = {}
        for u in to_send:
            merge_data[u.email] = {
                "first_name": getattr(u, "first_name", "") or "",
                "last_name": getattr(u, "last_name", "") or "",
                "email": u.email or "",
                "full_name": (f"{getattr(u, 'first_name', '')} {getattr(u, 'last_name', '')}" ).strip(),
                "username": getattr(u, "username", "") or "",
            }

        sent_count = 0
        try:
            msg = AnymailMessage(
                subject=subject_template,
                body=text_template,
                from_email=from_email,
                to=recipient_emails,
            )
            msg.attach_alternative(html_template, "text/html")
            msg.merge_data = merge_data  # per-recipient variables

            msg.send(fail_silently=False)

            # anymail_status provides per-recipient details
            status = getattr(msg, "anymail_status", None)
            recipient_statuses = {}
            if status is not None:
                # dict: email -> {status, message_id, ...}
                recipient_statuses = status.recipients

            for u in to_send:
                email = u.email
                st = recipient_statuses.get(email)
                if st is None or st.status == "queued" or st.status == "sent":
                    EmailSendLog.objects.create(
                        template=template,
                        user=u,
                        email=email,
                        status=EmailSendLog.STATUS_SENT,
                        message_id=getattr(st, "message_id", None) if st else None,
                    )
                    sent_count += 1
                else:
                    EmailSendLog.objects.create(
                        template=template,
                        user=u,
                        email=email,
                        status=EmailSendLog.STATUS_FAILED,
                        error=f"ESP status: {st.status}",
                        message_id=getattr(st, "message_id", None),
                    )
        except Exception as e:  # noqa: BLE001
            # Log a failure for each intended recipient
            for u in to_send:
                EmailSendLog.objects.create(
                    template=template,
                    user=u,
                    email=u.email,
                    status=EmailSendLog.STATUS_FAILED,
                    error=str(e),
                )
            self.stderr.write(self.style.ERROR(f"Batch send failed: {e}"))

        # Update last_sent_at on the template
        template.last_sent_at = timezone.now()
        template.save(update_fields=["last_sent_at"])

        self.stdout.write(self.style.SUCCESS(f"Sent {sent_count} emails."))

    def _get_template(self, options) -> EmailTemplate:
        template_id = options.get('template_id')
        template_name = options.get('template_name')
        if template_id is not None:
            try:
                return EmailTemplate.objects.get(pk=template_id)
            except EmailTemplate.DoesNotExist as e:
                raise CommandError(f"EmailTemplate with id={template_id} does not exist") from e
        else:
            try:
                return EmailTemplate.objects.get(name=template_name)
            except EmailTemplate.DoesNotExist as e:
                raise CommandError(f"EmailTemplate with name='{template_name}' does not exist") from e

    @staticmethod
    def _html_to_text(html: str) -> str:
        # Minimal fallback: remove tags; KISS for announcements
        import re
        text = re.sub(r'<\s*br\s*/?>', '\n', html, flags=re.I)
        text = re.sub(r'<[^>]+>', '', text)
        return re.sub(r'\n\n+', '\n\n', text).strip()

    @staticmethod
    def _convert_django_vars_to_mailgun(s: str) -> str:
        """
        Convert common Django template variables like {{ user.first_name }} to
        Mailgun recipient variable syntax %recipient.first_name% for use with
        Anymail merge_data. Keeps KISS: only a few common fields.
        """
        import re

        replacements = {
            r"\{\{\s*user\.first_name\s*\}\}": "%recipient.first_name%",
            r"\{\{\s*user\.last_name\s*\}\}": "%recipient.last_name%",
            r"\{\{\s*user\.email\s*\}\}": "%recipient.email%",
            r"\{\{\s*user\.username\s*\}\}": "%recipient.username%",
            r"\{\{\s*user\.get_full_name\s*\}\}": "%recipient.full_name%",
        }

        out = s
        for pattern, repl in replacements.items():
            out = re.sub(pattern, repl, out)
        return out
