# indabom
A simple bill of materials web app using [django-bom](https://github.com/mpkasp/django-bom).

- Master parts list with indented bill of materials
- Octopart price matching
- BOM Cost reporting, with sourcing recommendations

## Local Dev

Install django-bom locally as a sibling directory to indabom then in this directory run:

```shell
pipenv sync
# Install django-bom in editable mode for local dev
pipenv run pip install -e ../django-bom
pipenv shell
python manage.py migrate
python manage.py runserver
```

## Stripe
- To sync models, call `python manage.py djstripe_sync_models`
- Set up stripe cli to forward events to local webhook endpoint here using:
`stripe listen --forward-to localhost:8000/stripe/webhook/` then updating DJSTRIPE_WEBHOOK_SECRET in `.env`
- Test stripe using [this card info](https://stripe.com/docs/testing).

## MacOS Install
If issues installing mysqlclient on Apple Silicon MacOS [try](https://github.com/Homebrew/homebrew-core/issues/130258):

```console
$ export MYSQLCLIENT_LDFLAGS=$(pkg-config --libs mysqlclient)
$ export MYSQLCLIENT_CFLAGS=$(pkg-config --cflags mysqlclient)
$ pip install mysqlclient
```

## Deploying

To deploy simply:

```
git checkout prod
git merge --ff-only master
git push
```

Secrets are managed through GCP [Secret Manager](https://cloud.google.com/sdk/gcloud/reference/secrets). To update secrets for a respective environment, change to the correct project (using the gcloud PROJECT_ID) then run:

```console
gcloud secrets versions add django_settings_dev --data-file=.env.dev
gcloud secrets versions add django_settings --data-file=.env.prod
```

Build and deploy is run automagically using GCP [Cloud Build](https://cloud.google.com/build/docs/overview). (We tried github actions, but had trouble finding a way to run management commands thru cloud run on github actions.)