#!/bin/bash
gcloud secrets delete django_settings --quiet
gcloud secrets create django_settings --data-file .env.prod
gcloud secrets add-iam-policy-binding django_settings \
    --member serviceAccount:449904336434-compute@developer.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor
gcloud secrets add-iam-policy-binding django_settings \
    --member serviceAccount:449904336434@cloudbuild.gserviceaccount.com \
    --role roles/secretmanager.secretAccessor