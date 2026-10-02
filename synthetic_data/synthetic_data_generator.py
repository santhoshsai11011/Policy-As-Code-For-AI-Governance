import random
import string

import pandas as pd
from faker import Faker


# ============================================================
# CONFIGURATION
# ============================================================

NUMBER_OF_RECORDS = 250

OUTPUT_FILE = "synthetic_data/synthetic_dataset.xlsx"

# 10% of records will receive additional random overlap
OVERLAP_RECORD_PERCENTAGE = 0.10

fake = Faker("en_IN")


# ============================================================
# DATASET COLUMNS
# ============================================================

COLUMNS = [
    "record_id",
    "customer_name",
    "email",
    "phone",
    "address",
    "dob",
    "gender",
    "passport_number",
    "ni_number",
    "credit_card_number",
    "bank_account",
    "medical_condition",
    "ethnicity",
    "religion",
    "political_view",
    "employee_id",
    "department",
    "job_role",
    "customer_id",
    "ip_address",
    "feedback",
]


# All columns that can contain policy-related data.
# record_id and feedback are excluded from random overlap.
REGULAR_COLUMNS = [
    column
    for column in COLUMNS
    if column not in ["record_id", "feedback"]
]


# ============================================================
# RANDOM VALUE OPTIONS
# ============================================================

GENDERS = [
    "Male",
    "Female",
]

MEDICAL_CONDITIONS = [
    "Asthma",
    "Diabetes",
    "Hypertension",
    "Migraine",
    "Arthritis",
    "None",
]

ETHNICITIES = [
    "Asian",
    "Black",
    "White",
    "Mixed",
    "Other",
]

RELIGIONS = [
    "Hindu",
    "Christian",
    "Muslim",
    "Sikh",
    "Buddhist",
    "Other",
]

POLITICAL_VIEWS = [
    "Liberal",
    "Conservative",
    "Moderate",
    "Other",
]

DEPARTMENTS = [
    "Engineering",
    "Finance",
    "Marketing",
    "Human Resources",
    "Operations",
    "Sales",
    "Information Technology",
]

JOB_ROLES = [
    "Software Engineer",
    "Data Analyst",
    "Data Scientist",
    "Manager",
    "HR Executive",
    "Accountant",
    "Marketing Executive",
    "Business Analyst",
]


# ============================================================
# BANKING FEEDBACK
# ============================================================

FEEDBACK_SENTENCES = [
    "Pretty easy to use overall, but the transfer page was a little slow.",
    "Payment went through without any problems.",
    "Could not log in for a few minutes this morning.",
    "Really useful for checking the balance quickly.",
    "OTP took too long to arrive.",
    "Transaction history needs better filtering options.",
    "Much easier to manage cards through the app now.",
    "Had trouble adding a new beneficiary.",
    "Everything worked smoothly during the transfer.",
    "Would be helpful to get clearer messages when payments fail.",
    "Fast enough for checking balances and recent transactions.",
    "Bank transfer was still showing as pending after several minutes.",
    "Quite convenient for regular payments.",
    "Login worked after requesting the OTP again.",
    "Some screens take longer than expected to load.",
    "Easy to find recent transactions and account details.",
    "Payment failed once and worked after trying again.",
    "The transfer confirmation was not displayed immediately.",
    "Really convenient for keeping track of daily transactions.",
    "Could use a simpler way to download account statements.",
    "Card payment was processed quickly.",
    "The app has been reliable for checking recent spending.",
    "Had to retry the payment before it went through.",
    "Finding the account balance was straightforward.",
    "The beneficiary setup could be easier to understand.",
    "Transfer completed successfully and the confirmation arrived quickly.",
    "The app froze briefly while opening transaction history.",
    "Would like better notifications for incoming payments.",
    "Cash withdrawal details were easy to check.",
    "The payment screen could be a little clearer.",
    "Account statements take too long to load sometimes.",
    "Adding a new payee worked without any issues.",
    "The card management section is simple to navigate.",
    "Payment was declined and the reason was not very clear.",
    "The balance updated almost immediately after the transfer.",
    "Could not find the option to change the transaction limit.",
    "The banking app feels much faster after the latest update.",
    "Transfer details were easy to review before confirming.",
    "The notification for the payment arrived late.",
    "Checking previous transactions is very convenient.",
    "The app requested OTP several times during login.",
    "Everything was fine except the slow loading time.",
    "It was easy to move money between accounts.",
    "The payment receipt was useful for keeping track of the transaction.",
    "Would be nice to have more control over transaction alerts.",
    "The card payment appeared correctly in the transaction history.",
    "Had some difficulty finding the account statement section.",
    "The transfer was completed but the status took time to update.",
    "Overall, the payment process was straightforward.",
]


# ============================================================
# CUSTOM IDENTIFIER GENERATORS
# ============================================================

def generate_passport_number():
    letters = "".join(
        random.choices(string.ascii_uppercase, k=2)
    )

    numbers = "".join(
        random.choices(string.digits, k=7)
    )

    return letters + numbers


def generate_ni_number():
    letters = "".join(
        random.choices(string.ascii_uppercase, k=2)
    )

    numbers = "".join(
        random.choices(string.digits, k=6)
    )

    final_letter = random.choice(
        string.ascii_uppercase
    )

    return f"{letters} {numbers} {final_letter}"


def generate_bank_account():
    return "".join(
        random.choices(string.digits, k=10)
    )


def generate_employee_id():
    return (
        "EMP-"
        + "".join(
            random.choices(string.digits, k=6)
        )
    )


def generate_customer_id():
    return (
        "CUS-"
        + "".join(
            random.choices(string.digits, k=8)
        )
    )


# ============================================================
# VALUE GENERATORS
# ============================================================

VALUE_GENERATORS = {

    "customer_name":
        lambda: fake.name(),

    "email":
        lambda: fake.email(),

    "phone":
        lambda: fake.phone_number(),

    "address":
        lambda: fake.address().replace(
            "\n",
            ", "
        ),

    "dob":
        lambda: fake.date_of_birth(
            minimum_age=18,
            maximum_age=80
        ).isoformat(),

    "gender":
        lambda: random.choice(
            GENDERS
        ),

    "passport_number":
        generate_passport_number,

    "ni_number":
        generate_ni_number,

    "credit_card_number":
        fake.credit_card_number,

    "bank_account":
        generate_bank_account,

    "medical_condition":
        lambda: random.choice(
            MEDICAL_CONDITIONS
        ),

    "ethnicity":
        lambda: random.choice(
            ETHNICITIES
        ),

    "religion":
        lambda: random.choice(
            RELIGIONS
        ),

    "political_view":
        lambda: random.choice(
            POLITICAL_VIEWS
        ),

    "employee_id":
        generate_employee_id,

    "department":
        lambda: random.choice(
            DEPARTMENTS
        ),

    "job_role":
        lambda: random.choice(
            JOB_ROLES
        ),

    "customer_id":
        generate_customer_id,

    "ip_address":
        fake.ipv4,
}


# ============================================================
# BASE FILL RATE
# ============================================================

def generate_fill_rate():
    """
    Generate a random base fill rate between 5% and 8%.
    """

    return random.uniform(
        0.05,
        0.08
    )


# ============================================================
# GENERATE ONE COLUMN
# ============================================================

def generate_column_values(column_name):

    fill_rate = generate_fill_rate()

    number_of_values = round(
        NUMBER_OF_RECORDS * fill_rate
    )

    selected_indices = random.sample(
        range(NUMBER_OF_RECORDS),
        number_of_values
    )

    values = [
        None
        for _ in range(NUMBER_OF_RECORDS)
    ]

    generator = VALUE_GENERATORS[
        column_name
    ]

    for index in selected_indices:

        values[index] = generator()

    print(
        f"{column_name:<20} "
        f"base fill rate: "
        f"{fill_rate * 100:5.2f}% | "
        f"values: {number_of_values:3d}"
    )

    return values


# ============================================================
# GENERATE FEEDBACK
# ============================================================

def generate_feedback_values():

    values = []

    for _ in range(NUMBER_OF_RECORDS):

        values.append(
            random.choice(
                FEEDBACK_SENTENCES
            )
        )

    print(
        f"{'feedback':<20} "
        f"fill rate: 100.00% | "
        f"values: {NUMBER_OF_RECORDS:3d}"
    )

    return values


# ============================================================
# APPLY RANDOM COLUMN OVERLAP
# ============================================================

def apply_random_overlap(data):

    """
    Add additional random column overlap to 10% of records.

    Example:

    A normal record may have:
        customer_name = value
        email = None
        dob = None

    If this record is selected for overlap, the function
    randomly selects additional empty columns and fills them.

    No policy-specific scenarios are created.
    The columns are selected completely randomly.
    """

    overlap_record_count = round(
        NUMBER_OF_RECORDS
        * OVERLAP_RECORD_PERCENTAGE
    )

    overlap_record_indices = random.sample(
        range(NUMBER_OF_RECORDS),
        overlap_record_count
    )

    print()
    print("=" * 70)
    print("APPLYING RANDOM COLUMN OVERLAP")
    print("=" * 70)

    print(
        f"Overlap percentage : "
        f"{OVERLAP_RECORD_PERCENTAGE * 100:.0f}%"
    )

    print(
        f"Overlap records    : "
        f"{overlap_record_count}"
    )

    print()

    total_added_values = 0

    for index in overlap_record_indices:

        # Find columns that are currently empty
        empty_columns = [
            column_name
            for column_name in REGULAR_COLUMNS
            if pd.isna(
                data[column_name][index]
            )
        ]

        if len(empty_columns) < 2:
            continue

        # Randomly choose 2-4 additional columns
        maximum_columns = min(
            4,
            len(empty_columns)
        )

        number_of_overlap_columns = random.randint(
            2,
            maximum_columns
        )

        selected_columns = random.sample(
            empty_columns,
            number_of_overlap_columns
        )

        print(
            f"Record {index + 1:3d} -> "
            f"{', '.join(selected_columns)}"
        )

        for column_name in selected_columns:

            generator = VALUE_GENERATORS[
                column_name
            ]

            data[column_name][index] = generator()

            total_added_values += 1

    print()
    print(
        f"Additional values added: "
        f"{total_added_values}"
    )

    print("=" * 70)

    return data


# ============================================================
# GENERATE DATASET
# ============================================================

def generate_dataset():

    print("=" * 70)
    print("SYNTHETIC DATASET GENERATOR")
    print("=" * 70)

    print(
        f"Records                 : "
        f"{NUMBER_OF_RECORDS}"
    )

    print(
        "Base regular columns    : "
        "5% - 8%"
    )

    print(
        "Feedback                : "
        "100%"
    )

    print(
        f"Overlap records         : "
        f"{OVERLAP_RECORD_PERCENTAGE * 100:.0f}%"
    )

    print()

    data = {}

    # --------------------------------------------------------
    # RECORD ID
    # --------------------------------------------------------

    data["record_id"] = list(
        range(
            1,
            NUMBER_OF_RECORDS + 1
        )
    )

    # --------------------------------------------------------
    # REGULAR COLUMNS
    # --------------------------------------------------------

    for column_name in REGULAR_COLUMNS:

        data[column_name] = (
            generate_column_values(
                column_name
            )
        )

    # --------------------------------------------------------
    # FEEDBACK
    # --------------------------------------------------------

    data["feedback"] = (
        generate_feedback_values()
    )

    # --------------------------------------------------------
    # RANDOM OVERLAP
    # --------------------------------------------------------

    data = apply_random_overlap(
        data
    )

    # --------------------------------------------------------
    # CREATE DATAFRAME
    # --------------------------------------------------------

    dataframe = pd.DataFrame(
        data
    )

    # Make sure column order is exactly fixed
    dataframe = dataframe[
        COLUMNS
    ]

    return dataframe


# ============================================================
# SAVE DATASET
# ============================================================

def save_dataset(dataframe):

    from datetime import datetime
    from zoneinfo import ZoneInfo

    created_at = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    created_date = created_at.strftime("%d-%m-%Y")
    created_time = created_at.strftime("%I:%M:%S %p")
    created_datetime = created_at.strftime(
        "%d-%m-%Y %I:%M:%S %p"
    )

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl"
    ) as writer:

        # Main synthetic dataset
        dataframe.to_excel(
            writer,
            sheet_name="Synthetic Data",
            index=False
        )

        # Metadata sheet
        metadata = pd.DataFrame({
            "Property": [
                "Created Date",
                "Created Time",
                "Created Date & Time",
                "Timezone"
            ],
            "Value": [
                created_date,
                created_time,
                created_datetime,
                "Asia/Kolkata (IST)"
            ]
        })

        metadata.to_excel(
            writer,
            sheet_name="Metadata",
            index=False
        )

    print()
    print("=" * 70)
    print("DATASET GENERATED SUCCESSFULLY")
    print("=" * 70)

    print(f"Rows    : {len(dataframe)}")
    print(f"Columns : {len(dataframe.columns)}")
    print(f"Output  : {OUTPUT_FILE}")
    print(f"Created : {created_datetime} IST")

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    dataframe = generate_dataset()

    save_dataset(
        dataframe
    )