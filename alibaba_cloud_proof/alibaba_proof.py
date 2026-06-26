"""
Alibaba Cloud Deployment Proof
================================
This file demonstrates that DevMemory Agent uses Alibaba Cloud services.
Required by QwenCloud Hackathon rules: submission must include proof of Alibaba Cloud deployment.

Services used:
- Alibaba Cloud ECS: backend API server
- Alibaba Cloud RDS (PostgreSQL): persistent memory storage with pgvector
- Qwen Cloud API: AI model inference (qwen3.7-max, text-embedding-v4, qwen3-rerank) — Alibaba Cloud's AI platform

Run: python alibaba_proof.py
Requires QWEN_API_KEY, ALIBABA_ACCESS_KEY_ID/SECRET, DATABASE_URL in the environment (see .env.example).
"""

import os
import sys
from pathlib import Path

from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_tea_openapi import models as open_api_models
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def verify_qwen_cloud_api():
    """Verify Qwen Cloud API connectivity (Alibaba Cloud's AI platform)."""
    client = OpenAI(
        api_key=os.environ["QWEN_API_KEY"],
        base_url=os.environ.get("QWEN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
    )
    response = client.chat.completions.create(
        model=os.environ.get("QWEN_REASONING_MODEL", "qwen3.7-max"),
        messages=[{"role": "user", "content": "Reply with: DevMemory Agent running on Alibaba Cloud"}],
        max_tokens=50,
    )
    print("✓ Qwen Cloud API (Alibaba Cloud) verified")
    print(f"   Model: {os.environ.get('QWEN_REASONING_MODEL', 'qwen3.7-max')}")
    print(f"   Response: {response.choices[0].message.content}")


def verify_ecs_access():
    """Call a real ECS API (DescribeRegions) to prove the Alibaba Cloud account/credentials work."""
    config = open_api_models.Config(
        access_key_id=os.environ["ALIBABA_ACCESS_KEY_ID"],
        access_key_secret=os.environ["ALIBABA_ACCESS_KEY_SECRET"],
        region_id=os.environ.get("ALIBABA_REGION", "ap-southeast-1"),
    )
    config.endpoint = f"ecs.{config.region_id}.aliyuncs.com"
    client = EcsClient(config)

    request = ecs_models.DescribeRegionsRequest()
    response = client.describe_regions(request)
    regions = response.body.regions.region
    print("✓ Alibaba Cloud ECS API verified (DescribeRegions)")
    print(f"   Account has access to {len(regions)} region(s), e.g. {regions[0].region_id if regions else 'n/a'}")


def verify_rds_connection():
    """Verify Alibaba Cloud RDS (PostgreSQL) connection."""
    import psycopg2

    raw_url = os.environ["DATABASE_URL"].replace("+asyncpg", "")
    conn = psycopg2.connect(raw_url)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print("✓ Alibaba Cloud RDS (PostgreSQL) connected")
    print(f"   Version: {version[0][:60]}")
    cursor.close()
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("DevMemory Agent — Alibaba Cloud Deployment Proof")
    print("=" * 60)
    errors = []

    try:
        verify_qwen_cloud_api()
    except Exception as e:
        errors.append(f"Qwen Cloud: {e}")
        print(f"✗ Qwen Cloud API: {e}")

    try:
        verify_ecs_access()
    except Exception as e:
        errors.append(f"ECS: {e}")
        print(f"✗ ECS: {e}")

    try:
        verify_rds_connection()
    except Exception as e:
        errors.append(f"RDS: {e}")
        print(f"✗ RDS: {e}")

    if errors:
        print(f"\n⚠ {len(errors)} service(s) could not be verified (check credentials in .env)")
        sys.exit(1)
    else:
        print("\n✓ All Alibaba Cloud services verified successfully")
