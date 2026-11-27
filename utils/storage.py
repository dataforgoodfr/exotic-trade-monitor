#!/usr/bin/env python
"""
Helpers S3 pour Clever Cloud Cellar (object storage privé par défaut).

Les opérations sont pensées par DOSSIER (un dossier source = un ensemble de fichiers),
pour coller à la structure dbt_ETM/input_sources/<source>/last_version|archive/<date>/.

Variables d'environnement attendues (via .env en local, injectées
directement par Clever Cloud en production) :

    CLEVER_KEY_ID
    CLEVER_KEY_SECRET
"""

import json
import os
from pathlib import Path

import boto3
from botocore.client import Config
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(usecwd=True))

ACCESS_KEY = os.getenv("CLEVER_KEY_ID")
SECRET_KEY = os.getenv("CLEVER_KEY_SECRET")
ENDPOINT_URL = "https://cellar-c2.services.clever-cloud.com"
REGION_NAME = "par"
BUCKET_NAME = "extract"

_s3_client = None


def get_s3_client():
    """Crée (une seule fois) et retourne un client S3 configuré pour Cellar."""
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=REGION_NAME,
            endpoint_url=ENDPOINT_URL,
            aws_access_key_id=ACCESS_KEY,
            aws_secret_access_key=SECRET_KEY,
            config=Config(
                signature_version="s3v4",
                request_checksum_calculation="WHEN_REQUIRED",
                response_checksum_validation="WHEN_REQUIRED",
            ),
        )
    return _s3_client


def upload_folder(local_dir: str | Path, source_folder: str) -> None:
    """Upload tous les fichiers d'un dossier local sous source_folder sur Cellar."""
    local_dir = Path(local_dir)
    if not local_dir.is_dir():
        raise NotADirectoryError(f"Dossier introuvable : {local_dir}")

    files = [p for p in local_dir.rglob("*") if p.is_file()]
    if not files:
        print(f"⚠ aucun fichier dans {local_dir}, rien à uploader")
        return

    s3 = get_s3_client()
    print(
        f"📦 {local_dir} → s3://{BUCKET_NAME}/{source_folder}/ ({len(files)} fichiers)"
    )
    for file in files:
        relative_path = file.relative_to(local_dir).as_posix()
        remote_key = f"{source_folder}/{relative_path}"
        print(f"  ⬆ {file.name} → s3://{BUCKET_NAME}/{remote_key}")
        s3.upload_file(str(file), BUCKET_NAME, remote_key)
    print("✓ upload du dossier terminé")


def upload_json(data: dict, remote_key: str) -> None:
    """Upload un petit objet JSON (ex: métadonnées de version)."""
    get_s3_client().put_object(
        Bucket=BUCKET_NAME,
        Key=remote_key,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


if __name__ == "__main__":
    client = get_s3_client()
    response = client.list_objects_v2(Bucket=BUCKET_NAME)
    for obj in response.get("Contents", []):
        print(obj["Key"])
