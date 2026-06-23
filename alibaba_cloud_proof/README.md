# Alibaba Cloud Deployment Proof

Proof that DevMemory Agent runs on Alibaba Cloud infrastructure, as required by the
QwenCloud Global AI Hackathon rules.

## Services Used

| Service | Purpose |
|---|---|
| Alibaba Cloud ECS | Hosts the backend FastAPI + MCP server |
| Alibaba Cloud RDS (PostgreSQL 16 + pgvector) | Persistent memory storage |
| Qwen Cloud API | AI inference (qwen3.7-max, text-embedding-v4, qwen3-rerank) — Alibaba Cloud's AI platform |

## How to Run

```bash
cd alibaba_cloud_proof
pip install -r ../backend/requirements.txt
```

Set these in your environment (or `../.env`):

```bash
export QWEN_API_KEY=your_qwen_api_key
export ALIBABA_ACCESS_KEY_ID=your_access_key_id
export ALIBABA_ACCESS_KEY_SECRET=your_access_key_secret
export ALIBABA_REGION=ap-southeast-1
export DATABASE_URL=postgresql+asyncpg://user:pass@your-rds-host:5432/devmemory
```

```bash
python alibaba_proof.py
```

Each check (Qwen Cloud, ECS, RDS) runs independently and prints ✓ or ✗ — the
script exits non-zero if any service couldn't be verified, but doesn't crash
on a single failure, so you can see exactly which credential or service needs
attention.
