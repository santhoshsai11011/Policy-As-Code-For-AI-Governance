import json
import re
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent

RULES_PATH = BASE_DIR / "extracted_text" / "rules.json"
REGO_DIR = BASE_DIR / "policies" / "rego"
REGO_PATH = REGO_DIR / "policy.rego"

POLICY_RESULTS_EXCEL_PATH = (
    REGO_DIR / "policy_results.xlsx"
)


def load_rules():
    """
    Load extracted policy rules from rules.json.
    """

    if not RULES_PATH.exists():
        raise FileNotFoundError(
            f"Rules file not found: {RULES_PATH}"
        )

    with open(RULES_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "rules" not in data:
        raise ValueError(
            "rules.json does not contain a 'rules' field."
        )

    return data["rules"]


def get_display_rule_id(rule: dict) -> str:
    """
    Build the user-facing policy rule ID.

    Examples:
        PII + 01   -> PII-01
        SPII + 03  -> SPII-03
        CPII + 01  -> CPII-01
    """

    category = str(rule["category"]).strip()
    rule_id = str(rule["rule_id"]).strip()

    return f"{category}-{rule_id}"


def safe_rule_name(rule: dict) -> str:
    """
    Convert the policy rule ID into a valid Rego identifier.

    Examples:
        PII-01  -> rule_PII_01
        SPII-03 -> rule_SPII_03
        CPII-01 -> rule_CPII_01
    """

    display_rule_id = get_display_rule_id(rule)

    cleaned = re.sub(
        r"[^a-zA-Z0-9_]",
        "_",
        display_rule_id,
    )

    return f"rule_{cleaned}"


def column_present_expression(column: str) -> str:
    """
    Generate a Rego expression that checks whether
    a dataset column contains a non-empty value.
    """

    column_json = json.dumps(column)

    return (
        f'object.get(input, {column_json}, "") != ""'
    )


def condition_to_alternatives(condition: dict) -> list[list[str]]:
    """
    Convert a condition tree into alternative Rego condition
    bodies.

    Each returned list represents one complete condition body.

    Example:

        A AND B

    becomes:

        [
            [A, B]
        ]

    While:

        A OR B

    becomes:

        [
            [A],
            [B]
        ]

    And:

        A AND (B OR C)

    becomes:

        [
            [A, B],
            [A, C]
        ]

    This allows OR conditions to be represented using multiple
    Rego rule bodies without using the `or` keyword.
    """

    operator = condition.get("operator")
    fields = condition.get("fields", [])

    if not fields:

        if operator == "AND":
            return [[]]

        if operator == "OR":
            return []

        raise ValueError(
            f"Unsupported empty condition operator: {operator}"
        )

    # ---------------------------------------------------------
    # Convert every field into its possible alternatives
    # ---------------------------------------------------------

    field_alternatives = []

    for field in fields:

        column = field.get("column")
        required = field.get("required", True)
        nested_condition = field.get("condition")

        # -----------------------------------------------------
        # Base field condition
        # -----------------------------------------------------

        if required is False:

            base_alternatives = [
                []
            ]

        elif column is not None:

            base_alternatives = [
                [
                    column_present_expression(column)
                ]
            ]

        else:

            # The policy refers to something that does not
            # exist in the fixed synthetic dataset.
            base_alternatives = []

        # -----------------------------------------------------
        # Nested condition
        # -----------------------------------------------------

        if (
            isinstance(nested_condition, dict)
            and nested_condition.get("fields")
        ):

            nested_alternatives = (
                condition_to_alternatives(
                    nested_condition
                )
            )

            combined = []

            for base in base_alternatives:
                for nested in nested_alternatives:

                    combined.append(
                        base + nested
                    )

            base_alternatives = combined

        field_alternatives.append(
            base_alternatives
        )

    # ---------------------------------------------------------
    # AND
    # ---------------------------------------------------------

    if operator == "AND":

        alternatives = [[]]

        for alternatives_for_field in field_alternatives:

            new_alternatives = []

            for existing in alternatives:

                for current in alternatives_for_field:

                    new_alternatives.append(
                        existing + current
                    )

            alternatives = new_alternatives

        return alternatives

    # ---------------------------------------------------------
    # OR
    # ---------------------------------------------------------

    if operator == "OR":

        alternatives = []

        for alternatives_for_field in field_alternatives:

            alternatives.extend(
                alternatives_for_field
            )

        return alternatives

    raise ValueError(
        f"Unsupported condition operator: {operator}"
    )


def generate_rule_block(rule: dict) -> str:
    """
    Generate one Rego rule.

    OR conditions are represented as multiple Rego rule
    bodies using the same rule name.
    """

    display_rule_id = get_display_rule_id(rule)
    rule_name = safe_rule_name(rule)

    alternatives = condition_to_alternatives(
        rule["condition"]
    )

    lines = []

    lines.append(
        f"# {display_rule_id}: {rule['description']}"
    )

    # ---------------------------------------------------------
    # No evaluable alternatives
    # ---------------------------------------------------------

    if not alternatives:

        lines.append(
            f"{rule_name} if {{"
        )

        lines.append(
            "    false"
        )

        lines.append("}")

        return "\n".join(lines)

    # ---------------------------------------------------------
    # Generate each alternative as a separate Rego rule body
    # ---------------------------------------------------------

    for alternative_index, conditions in enumerate(
        alternatives
    ):

        lines.append(
            f"{rule_name} if {{"
        )

        if conditions:

            for expression in conditions:

                lines.append(
                    f"    {expression}"
                )

        else:

            lines.append(
                "    true"
            )

        lines.append("}")

        if alternative_index < len(alternatives) - 1:
            lines.append("")

    return "\n".join(lines)


def generate_triggered_rule_block(rule: dict) -> str:
    """
    Generate metadata for a triggered rule.
    """

    display_rule_id = get_display_rule_id(rule)
    rule_name = safe_rule_name(rule)

    metadata = {
        "rule_id": display_rule_id,
        "category": rule["category"],
        "description": rule["description"],
        "outcome": rule["outcome"],
        "explanation": rule["explanation"],
        "remediation": rule["remediation"],
    }

    metadata_json = json.dumps(
        metadata,
        ensure_ascii=False,
        indent=4,
    )

    return (
        f"triggered_rules contains {metadata_json} "
        f"if {rule_name}"
    )


def generate_rego(rules: list[dict]) -> str:
    """
    Generate the complete Rego policy.
    """

    parts = []

    # =========================================================
    # PACKAGE
    # =========================================================

    parts.append(
        """package policy

import rego.v1

"""
    )

    # =========================================================
    # EXTRACTED POLICY RULES
    # =========================================================

    parts.append(
        """# ========================================
# EXTRACTED POLICY RULES
# ========================================

"""
    )

    for rule in rules:

        parts.append(
            generate_rule_block(rule)
        )

        parts.append("\n\n")

    # =========================================================
    # TRIGGERED RULES
    # =========================================================

    parts.append(
        """# ========================================
# TRIGGERED RULES
# ========================================

"""
    )

    for rule in rules:

        parts.append(
            generate_triggered_rule_block(rule)
        )

        parts.append("\n\n")

    # =========================================================
    # OUTCOME DETECTION
    # =========================================================

    parts.append(
        """# ========================================
# OUTCOME DETECTION
# ========================================

has_block if {
    some rule in triggered_rules
    rule.outcome == "BLOCK"
}

has_flag if {
    some rule in triggered_rules
    rule.outcome == "FLAG"
}

"""
    )

    # =========================================================
    # FINAL DECISION
    # =========================================================

    parts.append(
        """# ========================================
# FINAL DECISION
# ========================================

decision := "BLOCK" if has_block

decision := "FLAG" if {
    not has_block
    has_flag
}

decision := "PASS" if {
    not has_block
    not has_flag
}

"""
    )

    # =========================================================
    # FINAL RESULT
    # =========================================================

    parts.append(
        """# ========================================
# FINAL RESULT
# ========================================

result := {
    "outcome": decision,
    "triggered_rules": [rule |
        some rule in triggered_rules
    ]
}
"""
    )

    return "".join(parts)


def save_rego(rego_policy: str):
    """
    Save the generated Rego policy.
    """

    REGO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        REGO_PATH,
        "w",
        encoding="utf-8",
    ) as file:

        file.write(rego_policy)


def save_policy_results_excel(rules: list[dict]):
    """
    Save the policy rule IDs and their outcomes
    into an Excel workbook.

    Sheets:
    1. Policy Results
    2. Metadata
    """

    from datetime import datetime
    from zoneinfo import ZoneInfo

    REGO_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    for rule in rules:

        rows.append({
            "Violation": get_display_rule_id(rule),
            "Action": rule["outcome"],
        })

    dataframe = pd.DataFrame(
        rows,
        columns=[
            "Violation",
            "Action",
        ],
    )

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
        POLICY_RESULTS_EXCEL_PATH,
        engine="openpyxl",
    ) as writer:

        # ----------------------------------------------------
        # POLICY RESULTS SHEET
        # ----------------------------------------------------

        dataframe.to_excel(
            writer,
            sheet_name="Policy Results",
            index=False,
        )

        worksheet = writer.sheets[
            "Policy Results"
        ]

        # Fixed column widths
        worksheet.column_dimensions[
            "A"
        ].width = 20

        worksheet.column_dimensions[
            "B"
        ].width = 15

        # Header formatting
        for cell in worksheet[1]:

            cell.font = cell.font.copy(
                bold=True
            )

            cell.alignment = cell.alignment.copy(
                horizontal="center",
                vertical="center",
            )

        # Center the data
        for row in worksheet.iter_rows(
            min_row=2
        ):

            for cell in row:

                cell.alignment = cell.alignment.copy(
                    horizontal="center",
                    vertical="center",
                )

        worksheet.freeze_panes = "A2"

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

        # Metadata column widths
        metadata_worksheet.column_dimensions[
            "A"
        ].width = 25

        metadata_worksheet.column_dimensions[
            "B"
        ].width = 35

        # Metadata header formatting
        for cell in metadata_worksheet[1]:

            cell.font = cell.font.copy(
                bold=True
            )

            cell.alignment = cell.alignment.copy(
                horizontal="center",
                vertical="center",
            )

        metadata_worksheet.freeze_panes = "A2"

    print(
        f"Policy results Excel saved to: "
        f"{POLICY_RESULTS_EXCEL_PATH}"
    )


def main():

    print("=" * 60)
    print("POLICY → REGO GENERATOR")
    print("=" * 60)

    print()
    print(f"Rules file : {RULES_PATH}")
    print(f"Rego file  : {REGO_PATH}")

    # =========================================================
    # LOAD RULES
    # =========================================================

    print()
    print("Loading extracted rules...")

    rules = load_rules()

    print(
        f"Rules loaded: {len(rules)}"
    )

    # =========================================================
    # SAVE POLICY RESULTS EXCEL
    # =========================================================

    print()
    print("Generating policy results Excel...")

    save_policy_results_excel(
        rules
    )

    # =========================================================
    # DISPLAY RULE IDS
    # =========================================================

    print()
    print("Policy rule IDs:")

    for rule in rules:

        display_rule_id = get_display_rule_id(
            rule
        )

        print(
            f"  {display_rule_id} "
            f"({rule['category']})"
        )

    # =========================================================
    # GENERATE REGO
    # =========================================================

    print()
    print("Generating Rego policy...")

    rego_policy = generate_rego(
        rules
    )

    print(
        f"Generated Rego characters: "
        f"{len(rego_policy)}"
    )

    # =========================================================
    # SAVE REGO
    # =========================================================

    print()
    print("Saving Rego policy...")

    save_rego(
        rego_policy
    )

    print()
    print(
        "Rego generation completed successfully."
    )

    print()
    print("Generated files:")

    print(REGO_PATH)
    print(POLICY_RESULTS_EXCEL_PATH)

    print("=" * 60)


if __name__ == "__main__":
    main()