# GCP configuration placeholders

Fill these in **locally**. Nothing is charged until you run `terraform apply` or use Vertex/GCS.

## 1. Runtime — `.env` (copy from `.env.example`)

```bat
copy .env.example .env
```

| Variable | Placeholder | What to set |
|----------|-------------|-------------|
| `GCP_PROJECT` | `your-gcp-project-id` | Your GCP project ID |
| `GOOGLE_CLOUD_PROJECT` | same | Same as above |
| `GCP_REGION` | `us-central1` | e.g. `asia-south1`, `europe-west1` |
| `GCP_ZONE` | `us-central1-a` (optional) | e.g. `asia-south1-a` |
| `DOCUMENTS_BUCKET` | `{project}-rag-documents` | After Terraform creates the bucket |
| `PROCESSED_BUCKET` | `{project}-rag-processed` | After Terraform |
| `VECTOR_INDEX_ID` | empty | After Vertex Vector Search deploy |
| `VECTOR_ENDPOINT_ID` | empty | After index endpoint deploy |

## 2. Terraform — `terraform.tfvars` (copy from example)

**Dev**

```bat
cd infra\terraform\environments\dev
copy terraform.tfvars.example terraform.tfvars
```

```hcl
project_id = "your-gcp-project-id"
region     = "us-central1"
# zone     = "us-central1-a"
```

**Prod** — same under `infra/terraform/environments/prod/`.

## 3. Do not commit

- `.env`
- `terraform.tfvars`
- Any key files

Only commit `.env.example` and `terraform.tfvars.example`.
