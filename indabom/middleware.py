from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect
from django.urls import resolve


class TermsAcceptanceMiddleware:
    """Require authenticated users to accept updated Terms/Privacy before continuing.

    Exempt URLs continue to work to avoid redirect loops and allow users to view
    terms, privacy, logout, static assets, etc.
    """

    EXEMPT_PATH_PREFIXES = (
        "/static/",
        settings.MEDIA_URL or "/media/",
    )

    EXEMPT_URL_NAMES = {
        'login', 'logout', 'signup',
        'terms-and-conditions', 'privacy-policy',
        'robots-file', 'sitemap',
        'password_reset', 'password_reset_done', 'password_reset_confirm', 'password_reset_complete',
        'update-terms',
        'stripe-webhook',
    }

    EXEMPT_PATHS = {
        '/privacy-policy/',
        '/terms-and-conditions/',
        '/update-terms/',
        '/robots.txt',
        '/sitemap.xml',
        '/webhooks/stripe/',
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        # Skip for unauthenticated users
        if not user or not user.is_authenticated:
            return self.get_response(request)

        # Exempt by path prefix (static/media)
        if any(request.path.startswith(prefix) for prefix in self.EXEMPT_PATH_PREFIXES if prefix):
            return self.get_response(request)

        # Exempt by admin path
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Exempt by exact path list
        if request.path in self.EXEMPT_PATHS:
            return self.get_response(request)

        # Exempt by resolved URL name when possible
        try:
            match = resolve(request.path)
            if match.url_name in self.EXEMPT_URL_NAMES:
                return self.get_response(request)
        except Exception:
            pass

        # Determine if new terms acceptance is required
        user_meta = getattr(user, 'indabom_meta', None)
        needs_acceptance = (
            user_meta is None or
            not getattr(user_meta, 'terms_accepted_at', None) or
            user_meta.terms_accepted_at < settings.NEW_TERMS_EFFECTIVE
        )

        if needs_acceptance and request.path != '/update-terms/':
            next_param = request.get_full_path()
            return redirect(f"/update-terms/?next={quote(next_param)}")

        return self.get_response(request)
