#!/bin/bash
# gcloud run deploy indabom --platform managed --region us-central1 --image gcr.io/my-project-1472838847531/indabom

SERVICE_URL=$(gcloud run services describe indabom --platform managed \
    --region us-central1 --format "value(status.url)")

gcloud run deploy indabom \
    --platform managed \
    --region us-central1 \
    --image gcr.io/my-project-1472838847531/indabom \
    --add-cloudsql-instances indabom:us-central1:prod-02 \
    --allow-unauthenticated \
    --set-env-vars CLOUDRUN_SERVICE_URL=$SERVICE_URL
    