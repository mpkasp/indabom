#!/bin/bash
gcloud builds submit --config cloudmigrate.yaml --substitutions _INSTANCE_NAME=prod-02,_REGION=us-central1