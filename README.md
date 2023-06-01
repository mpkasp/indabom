# indabom
A simple bill of materials web app using [django-bom](https://github.com/mpkasp/django-bom).

- Master parts list with indented bill of materials
- Octopart price matching
- BOM Cost reporting, with sourcing recommendations

## Stripe
To sync models, call `python manage.py djstripe_sync_models`
Need to use 2.4.1 due to [this issue](https://github.com/dj-stripe/dj-stripe/issues/1386)
Test stripe using [this card info](https://stripe.com/docs/testing).

## MacOS Install
If issues installing mysqlclient on Apple Silicon MacOS [try](https://github.com/Homebrew/homebrew-core/issues/130258):

```console
$ export MYSQLCLIENT_LDFLAGS=$(pkg-config --libs mysqlclient)
$ export MYSQLCLIENT_CFLAGS=$(pkg-config --cflags mysqlclient)
$ pip install mysqlclient
```