#!/usr/bin/env bash
# Deploy data-agent to Cloud Run (internal VPC / company project).
# Requires: gcloud authenticated, Artifact Registry repo exists.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-oppo-gcp-prod-digfood-129869}"
REGION="${REGION:-asia-southeast2}"
SERVICE="${SERVICE:-qpon-data-agent}"
IMAGE_REPO="${IMAGE_REPO:-${REGION}-docker.pkg.dev/${PROJECT_ID}/data-agent/${SERVICE}}"
SA_EMAIL="${SA_EMAIL:-qpon-data-agent@${PROJECT_ID}.iam.gserviceaccount.com}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "==> Building ${IMAGE_REPO}:latest"
gcloud builds submit --project="${PROJECT_ID}" --tag "${IMAGE_REPO}:latest" .

echo "==> Deploying Cloud Run service ${SERVICE}"
# Secrets must already exist in Secret Manager or be passed via --set-env-vars for non-secret config.
# Prefer Secret Manager mounts for keys.
gcloud run deploy "${SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_REPO}:latest" \
  --service-account="${SA_EMAIL}" \
  --allow-unauthenticated \
  --no-cpu-throttling \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --concurrency=20 \
  --max-instances=5 \
  --set-env-vars="BQ_PROJECT=${PROJECT_ID},BQ_LOCATION=${REGION},BQ_ALLOWED_DATASETS=qpon_rpt_d,qpon_dws_d,qpon_dwd_d,GEMINI_MODEL=gemini-2.5-flash,ENABLE_HTTP_ASK=false" \
  --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,FEISHU_APP_ID=feishu-app-id:latest,FEISHU_APP_SECRET=feishu-app-secret:latest,FEISHU_VERIFICATION_TOKEN=feishu-verification-token:latest,FEISHU_ENCRYPT_KEY=feishu-encrypt-key:latest"

echo "==> Service URL:"
gcloud run services describe "${SERVICE}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)'

echo "Done. Point Feishu event subscription Request URL to: <URL>/feishu/event"
