#!/bin/bash
# 1. Update secrets from .env.prod
gcloud secrets delete django_settings --quiet
gcloud secrets create django_settings --data-file .env.prod
gcloud secrets add-iam-policy-binding django_settings \
    --member serviceAccount:449904336434-compute@developer.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor
gcloud secrets add-iam-policy-binding django_settings \
    --member serviceAccount:449904336434@cloudbuild.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor

# 2. Run Cloud Build
gcloud builds submit --config cloudmigrate.yaml --substitutions _INSTANCE_NAME=prod-02,_REGION=us-central1

# 3. Deploy
SERVICE_URL=$(gcloud run services describe indabom --platform managed \
    --region us-central1 --format "value(status.url)")

gcloud run deploy indabom \
    --platform managed \
    --region us-central1 \
    --image gcr.io/my-project-1472838847531/indabom \
    --add-cloudsql-instances indabom:us-central1:prod-02 \
    --allow-unauthenticated \
    --set-env-vars CLOUDRUN_SERVICE_URL=$SERVICE_URL
    