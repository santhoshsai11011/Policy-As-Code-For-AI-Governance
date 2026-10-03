import json
import math
import os
from datetime import datetime

import psycopg
from psycopg.types.json import Jsonb


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set in the environment."
        )

    return psycopg.connect(database_url)


# ============================================================
# CLEAN VALUES
# ============================================================

def clean_value(value):
    if isinstance(value, float) and math.isnan(value):
        return None

    return value


def clean_record(record):
    cleaned = {}

    for key, value in record.items():

        if isinstance(value, dict):
            cleaned[key] = clean_record(value)

        elif isinstance(value, list):
            cleaned[key] = [
                clean_value(item)
                for item in value
            ]

        else:
            cleaned[key] = clean_value(value)

    return cleaned


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    id BIGSERIAL PRIMARY KEY,
                    run_number INTEGER NOT NULL,
                    run_date TIMESTAMPTZ NOT NULL,
                    policy_name TEXT,
                    dataset_name TEXT NOT NULL,
                    total_records INTEGER NOT NULL,
                    pass_count INTEGER NOT NULL,
                    flag_count INTEGER NOT NULL,
                    block_count INTEGER NOT NULL,
                    artifact_paths JSONB
                )
            """)
            
            cursor.execute("""
                ALTER TABLE runs
                ADD COLUMN IF NOT EXISTS artifact_paths JSONB
           """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS run_records (
                    id BIGSERIAL PRIMARY KEY,
                    run_id BIGINT NOT NULL
                        REFERENCES runs(id)
                        ON DELETE CASCADE,
                    record_id TEXT NOT NULL,
                    record_data JSONB NOT NULL,
                    outcome TEXT NOT NULL,
                    triggered_rules JSONB,
                    reason TEXT,
                    remediation TEXT
                )
            """)

        conn.commit()

    finally:
        conn.close()
# ============================================================
# SAVE RUN
# ============================================================

def save_run(
    records,
    dataset_name,
    policy_name="AI Training Data PII Policy"
):

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Generate next run number
            # ------------------------------------------------

            cursor.execute("""
                SELECT COALESCE(MAX(run_number), 0) + 1
                FROM runs
            """)

            run_number = cursor.fetchone()[0]

            # ------------------------------------------------
            # Calculate summary from ACTUAL OPA fields
            #
            # Evaluation results contain:
            #   result["outcome"]
            #   result["triggered_rules"]
            #   result["input"]
            #
            # They do NOT contain expected_outcome.
            # ------------------------------------------------

            total_records = len(records)

            pass_count = sum(
                1
                for record in records
                if record.get("outcome") == "PASS"
            )

            flag_count = sum(
                1
                for record in records
                if record.get("outcome") == "FLAG"
            )

            block_count = sum(
                1
                for record in records
                if record.get("outcome") == "BLOCK"
            )

            run_date = datetime.now().astimezone()

            # ------------------------------------------------
            # Insert run
            # ------------------------------------------------

            cursor.execute("""
                INSERT INTO runs (
                    run_number,
                    run_date,
                    policy_name,
                    dataset_name,
                    total_records,
                    pass_count,
                    flag_count,
                    block_count
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                RETURNING id
            """, (
                run_number,
                run_date,
                policy_name,
                dataset_name,
                total_records,
                pass_count,
                flag_count,
                block_count,
            ))

            run_id = cursor.fetchone()[0]

            # ------------------------------------------------
            # Insert evaluated records
            # ------------------------------------------------

            for result in records:

                input_record = result.get(
                    "input",
                    {}
                )

                input_record = clean_record(
                    dict(input_record)
                )

                triggered_rules = result.get(
                    "triggered_rules",
                    []
                )

                triggered_rule_ids = result.get(
                    "triggered_rule_ids",
                    []
                )

                # Keep the complete triggered-rule objects
                # in JSONB. Add rule IDs if necessary.
                stored_rules = []

                for rule in triggered_rules:

                    rule_copy = dict(rule)

                    stored_rules.append(
                        rule_copy
                    )

                # Store a compact structure containing
                # both rule IDs and complete rule details.
                triggered_rules_data = {
                    "rule_ids": triggered_rule_ids,
                    "rules": stored_rules,
                }

                cursor.execute("""
                    INSERT INTO run_records (
                        run_id,
                        record_id,
                        record_data,
                        outcome,
                        triggered_rules,
                        reason,
                        remediation
                    )
                    VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s
                    )
                """, (
                    run_id,
                    str(result.get("record_id")),
                    Jsonb(input_record),
                    result.get(
                        "outcome",
                        "PASS"
                    ),
                    Jsonb(triggered_rules_data),
                    "",
                    "",
                ))

        conn.commit()

        return run_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# ============================================================
# GET ALL RUNS
# ============================================================

def get_runs():

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT
                    id,
                    run_number,
                    run_date,
                    policy_name,
                    dataset_name,
                    total_records,
                    pass_count,
                    flag_count,
                    block_count,
                    artifact_paths
                FROM runs
                ORDER BY run_number DESC
            """)

            rows = cursor.fetchall()

            columns = [
                description.name
                for description in cursor.description
            ]

        return [
            dict(zip(columns, row))
            for row in rows
        ]

    finally:
        conn.close()


# ============================================================
# GET ONE COMPLETE RUN
# ============================================================

def get_run(run_id):

    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            # ------------------------------------------------
            # Run metadata
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    id,
                    run_number,
                    run_date,
                    policy_name,
                    dataset_name,
                    total_records,
                    pass_count,
                    flag_count,
                    block_count,
                    artifact_paths
                FROM runs
                WHERE id = %s
            """, (run_id,))

            run = cursor.fetchone()

            if run is None:
                return None

            run_columns = [
                description.name
                for description in cursor.description
            ]

            # ------------------------------------------------
            # Evaluated records
            # ------------------------------------------------

            cursor.execute("""
                SELECT
                    record_id,
                    record_data,
                    outcome,
                    triggered_rules
                FROM run_records
                WHERE run_id = %s
                ORDER BY record_id::INTEGER
            """, (run_id,))

            record_rows = cursor.fetchall()

        run_data = dict(
            zip(run_columns, run)
        )

        run_data["records"] = []

        for row in record_rows:

            (
                record_id,
                record_data,
                outcome,
                triggered_rules_data,
            ) = row

            record_data = (
                dict(record_data)
                if isinstance(record_data, dict)
                else json.loads(record_data)
            )

            triggered_rule_ids = []
            triggered_rules = []

            if triggered_rules_data:

                if isinstance(
                    triggered_rules_data,
                    dict
                ):
                    triggered_rule_ids = (
                        triggered_rules_data.get(
                            "rule_ids",
                            []
                        )
                    )

                    triggered_rules = (
                        triggered_rules_data.get(
                            "rules",
                            []
                        )
                    )

                elif isinstance(
                    triggered_rules_data,
                    list
                ):
                    triggered_rules = (
                        triggered_rules_data
                    )

                    triggered_rule_ids = [
                        rule.get("rule_id")
                        for rule in triggered_rules
                        if isinstance(rule, dict)
                        and rule.get("rule_id")
                    ]

            record = {
                "record_id": str(record_id),
                "outcome": outcome,
                "triggered_rule_ids": (
                    triggered_rule_ids
                ),
                "triggered_categories": [
                    rule.get("category")
                    for rule in triggered_rules
                    if isinstance(rule, dict)
                    and rule.get("category")
                ],
                "triggered_rules": triggered_rules,
                "input": clean_record(
                    record_data
                ),
            }

            run_data["records"].append(
                record
            )

        return run_data

    finally:
        conn.close()

# ============================================================
# UPDATE RUN ARTIFACT PATHS
# ============================================================

def update_run_artifact_paths(
    run_id,
    artifact_paths,
):
    conn = get_connection()

    try:
        with conn.cursor() as cursor:

            cursor.execute("""
                UPDATE runs
                SET
                    artifact_paths = %s
                WHERE id = %s
            """, (
                Jsonb(artifact_paths),
                run_id,
            ))

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
# ============================================================
# DIRECT TEST
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print("=" * 60)
    print("SUPABASE POSTGRESQL DATABASE INITIALIZED")
    print("=" * 60)

# ============================================================
# CREATE SIGNED DOWNLOAD URL
# ============================================================

def create_run_artifact_url(
    storage_path,
    expires_in=300,
):
    """
    Create a temporary signed URL for a private run artifact.
    """

    response = (
        supabase.storage
        .from_(BUCKET_NAME)
        .create_signed_url(
            storage_path,
            expires_in,
            {"download": True},
        )
    )

    return response["signedURL"]