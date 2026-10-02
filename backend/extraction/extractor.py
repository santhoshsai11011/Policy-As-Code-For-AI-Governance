import json
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import pandas as pd
from config.rule_schema import RULE_SCHEMA
from config.dataset_schema import POLICY_MAPPABLE_COLUMNS
from backend.extraction.prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from backend.extraction.validator import validate_rules


load_dotenv()


MODEL_NAME = "gpt-5.6-luna"

BASE_DIR = Path(__file__).resolve().parent.parent.parent

RULES_EXCEL_PATH = (
    BASE_DIR
    / "extracted_text"
    / "rules.xlsx"
)

def extract_rules(policy_text: str) -> dict:
    """
    Extract PII, SPII and CPII rules from policy text
    using OpenAI, then validate the extracted result.
    """

    # ========================================================
    # API KEY
    # ========================================================

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY environment variable is not set."
        )

    client = OpenAI(
        api_key=api_key
    )

    # ========================================================
    # BUILD PROMPT
    # ========================================================

    user_prompt = build_user_prompt(
        policy_text=policy_text,
        dataset_columns=POLICY_MAPPABLE_COLUMNS,
    )

    # ========================================================
    # EXTRACTION LOG
    # ========================================================

    print("=" * 60)
    print("OPENAI POLICY RULE EXTRACTION")
    print("=" * 60)

    print(
        f"Model: {MODEL_NAME}"
    )

    print(
        f"Policy characters: {len(policy_text)}"
    )

    print(
        f"Dataset columns: {len(POLICY_MAPPABLE_COLUMNS)}"
    )

    print(
        "Sending extraction request..."
    )

    # ========================================================
    # OPENAI REQUEST
    # ========================================================

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT,
        input=user_prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "policy_rules",
                "schema": RULE_SCHEMA,
                "strict": True,
            }
        },
    )

    # ========================================================
    # PARSE RESPONSE
    # ========================================================

    print(
        "OpenAI response received."
    )

    result = json.loads(
        response.output_text
    )
    save_rules_excel(result)

    print(
        f"Rules extracted: "
        f"{len(result.get('rules', []))}"
    )

    # ========================================================
    # VALIDATE
    # ========================================================

    print(
        "Validating extracted rules..."
    )

    validate_rules(result)

    print(
        "Rule validation: PASSED"
    )

    print("=" * 60)

    return result

def save_rules_excel(result: dict):
    """
    Save the complete LLM-generated rules JSON
    into a properly formatted Excel workbook.

    The workbook contains:
    1. Rules     - extracted policy rules
    2. Metadata  - creation date/time information
    """

    from datetime import datetime
    from zoneinfo import ZoneInfo

    RULES_EXCEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    for rule in result.get("rules", []):
        row = {}

        for key, value in rule.items():

            if isinstance(value, (dict, list)):
                row[key] = json.dumps(
                    value,
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                row[key] = value

        rows.append(row)

    dataframe = pd.DataFrame(rows)

    # ========================================================
    # CREATION TIMESTAMP
    # ========================================================

    created_at = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    created_date = created_at.strftime(
        "%d-%m-%Y"
    )

    created_time = created_at.strftime(
        "%I:%M:%S %p"
    )

    created_datetime = created_at.strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    # ========================================================
    # CREATE EXCEL WORKBOOK
    # ========================================================

    with pd.ExcelWriter(
        RULES_EXCEL_PATH,
        engine="openpyxl",
    ) as writer:

        # ----------------------------------------------------
        # RULES SHEET
        # ----------------------------------------------------

        dataframe.to_excel(
            writer,
            sheet_name="Rules",
            index=False,
        )

        worksheet = writer.sheets["Rules"]

        # ----------------------------------------------------
        # Freeze header row
        # ----------------------------------------------------

        worksheet.freeze_panes = "A2"

        # ----------------------------------------------------
        # Fixed column widths
        # ----------------------------------------------------

        column_widths = {
            "A": 12,   # rule_id
            "B": 12,   # category
            "C": 35,   # description
            "D": 35,   # policy_terms
            "E": 22,   # columns
            "F": 50,   # condition
            "G": 12,   # outcome
            "H": 40,   # explanation
            "I": 40,   # remediation
        }

        for column, width in column_widths.items():
            worksheet.column_dimensions[column].width = width

        # ----------------------------------------------------
        # Header formatting
        # ----------------------------------------------------

        for cell in worksheet[1]:
            cell.font = cell.font.copy(
                bold=True
            )

            cell.alignment = cell.alignment.copy(
                horizontal="center",
                vertical="center",
                wrap_text=True,
            )

        # ----------------------------------------------------
        # Data cell formatting
        # ----------------------------------------------------

        for row in worksheet.iter_rows(
            min_row=2
        ):
            for cell in row:
                cell.alignment = cell.alignment.copy(
                    vertical="top",
                    wrap_text=True,
                )

        # ----------------------------------------------------
        # Header row height
        # ----------------------------------------------------

        worksheet.row_dimensions[1].height = 25

        # ====================================================
        # METADATA SHEET
        # ====================================================

        metadata = pd.DataFrame({
            "Property": [
                "Created Date",
                "Created Time",
                "Created Date & Time",
                "Timezone",
            ],
            "Value": [
                created_date,
                created_time,
                created_datetime,
                "Asia/Kolkata (IST)",
            ],
        })

        metadata.to_excel(
            writer,
            sheet_name="Metadata",
            index=False,
        )

        metadata_worksheet = writer.sheets[
            "Metadata"
        ]

        # ----------------------------------------------------
        # Metadata formatting
        # ----------------------------------------------------

        metadata_worksheet.column_dimensions[
            "A"
        ].width = 25

        metadata_worksheet.column_dimensions[
            "B"
        ].width = 35

        for cell in metadata_worksheet[1]:
            cell.font = cell.font.copy(
                bold=True
            )

            cell.alignment = cell.alignment.copy(
                horizontal="center",
                vertical="center",
            )

        for row in metadata_worksheet.iter_rows(
            min_row=2
        ):
            for cell in row:
                cell.alignment = cell.alignment.copy(
                    vertical="center",
                )

        metadata_worksheet.freeze_panes = "A2"

    print(
        f"Formatted rules Excel saved to: "
        f"{RULES_EXCEL_PATH}"
    )