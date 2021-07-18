# indabom
A simple bill of materials web app using [django-bom](https://github.com/mpkasp/django-bom).

- Master parts list with indented bill of materials
- Octopart price matching
- BOM Cost reporting, with sourcing recommendations

## Stripe
To sync models, call `python manage.py djstripe_sync_models`
Need to use 2.4.1 due to [this issue](https://github.com/dj-stripe/dj-stripe/issues/1386)
Test stripe using [this card info](https://stripe.com/docs/testing).