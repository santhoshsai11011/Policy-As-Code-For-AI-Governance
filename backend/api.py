from pathlib import Path
import json

import pandas as pd
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from database.database import (
    initialize_database,
    save_run,
    get_runs,
    get_run,
    update_run_artifact_paths,
)
from backend.storage import (
    upload_run_artifacts,
    create_run_artifact_url,
)

from backend.ingestion.pdf_extractor import (
    extract_text_from_pdf,
)

from backend.extraction.extractor import extract_rules

from synthetic_data.synthetic_data_generator import (
    generate_dataset,
    save_dataset,
)

from backend.policy_engine.rego_generator import (
    load_rules,
    generate_rego,
    save_rego,
    save_policy_results_excel,
)

from backend.policy_engine.eval import (
    load_dataset,
    validate_dataset_columns,
    evaluate_dataset,
    calculate_summary,
    save_results,
    save_results_excel,
)



app = FastAPI()


# --------------------------------------------------
# Policy Processing Jobs
# --------------------------------------------------

POLICY_JOBS = {}


def update_policy_job(
    job_id,
    *,
    status=None,
    current_step=None,
    progress=None,
    message=None,
    result=None,
):
    job = POLICY_JOBS.get(job_id)

    if job is None:
        return

    if status is not None:
        job["status"] = status

    if current_step is not None:
        job["current_step"] = current_step

    if progress is not None:
        job["progress"] = progress

    if message is not None:
        job["message"] = message

    if result is not None:
        job["result"] = result






# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "https://policy-as-code-for-ai-governance.vercel.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

initialize_database()

# --------------------------------------------------
# Paths
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

POLICIES_DIR = BASE_DIR / "policies"
EXTRACTED_TEXT_DIR = BASE_DIR / "extracted_text"

POLICIES_DIR.mkdir(exist_ok=True)
EXTRACTED_TEXT_DIR.mkdir(exist_ok=True)


# --------------------------------------------------
# Fixed filenames
# --------------------------------------------------

# --------------------------------------------------
# Fixed filenames
# --------------------------------------------------

CURRENT_POLICY_PATH = POLICIES_DIR / "current_policy.pdf"
CURRENT_POLICY_ORIGINAL_FILENAME = "current_policy.pdf"

POLICY_TEXT_TXT_PATH = EXTRACTED_TEXT_DIR / "policy.txt"
CURRENT_RULES_PATH = EXTRACTED_TEXT_DIR / "rules.json"

RESULTS_DIR = BASE_DIR / "evaluation_results"
RESULTS_PATH = RESULTS_DIR / "results.json"
DASHBOARD_SUMMARY_EXCEL_PATH = RESULTS_DIR / "dashboard_summary.xlsx"


# --------------------------------------------------
# Health check
# --------------------------------------------------

@app.get("/")
def root():

    print("Backend health check received")

    return {
        "message": "Policy-As-Code API is running"
    }


# --------------------------------------------------
# Evaluation Results
# --------------------------------------------------

@app.get("/evaluation-results")
def get_evaluation_results():

    print("Evaluation results request received")

    if not RESULTS_PATH.exists():

        return {
            "success": False,
            "message": "Evaluation results not found."
        }

    with open(
        RESULTS_PATH,
        "r",
        encoding="utf-8"
    ) as file:

        results = json.load(file)

    return {
        "success": True,
        "results": results
    }


# --------------------------------------------------
# Synthetic Data Generation
# --------------------------------------------------

@app.post("/generate-data")
def generate_synthetic_data():

    print()
    print("=" * 60)
    print("SYNTHETIC DATA GENERATION REQUEST RECEIVED")
    print("=" * 60)

    try:

        dataframe = generate_dataset()

        save_dataset(dataframe)

        return {
            "success": True,
            "message": "Synthetic dataset generated successfully.",
            "filename": "synthetic_dataset.xlsx",
            "records": len(dataframe),
            "columns": len(dataframe.columns),
        }

    except Exception as error:

        print()
        print("=" * 60)
        print("SYNTHETIC DATA GENERATION FAILED")
        print("=" * 60)

        print(f"Error: {error}")

        return {
            "success": False,
            "message": f"Synthetic data generation failed: {str(error)}",
        }


# --------------------------------------------------
# Delete Previous Policy
# --------------------------------------------------

def delete_previous_policy():

    print()
    print("Removing previous policy data...")

    files_to_delete = [
        CURRENT_POLICY_PATH,
        POLICY_TEXT_TXT_PATH,
        CURRENT_RULES_PATH,
    ]

    for file_path in files_to_delete:

        if file_path.exists():

            file_path.unlink()

            print(f"Deleted: {file_path}")

        else:

            print(f"Not found: {file_path}")


# --------------------------------------------------
# PDF Upload + Complete Policy Processing
# --------------------------------------------------

def process_policy_upload(
    job_id,
    original_filename,
):
    try:

        # --------------------------------------------------
        # PDF INGESTION
        # --------------------------------------------------

        update_policy_job(
            job_id,
            status="processing",
            current_step="PDF Ingestion",
            progress=5,
            message="Reading and extracting text from the uploaded PDF.",
        )

        policy_text, pages = extract_text_from_pdf(
            CURRENT_POLICY_PATH,
            POLICY_TEXT_TXT_PATH,
        )

        update_policy_job(
            job_id,
            current_step="PDF Ingestion",
            progress=15,
            message="PDF text extraction completed.",
        )

        print()
        print(
            f"Combined policy text length: "
            f"{len(policy_text)} characters"
        )

        # --------------------------------------------------
        # RULE EXTRACTION
        # --------------------------------------------------

        update_policy_job(
            job_id,
            current_step="Rule Extraction",
            progress=20,
            message="Extracting PII, SPII and CPII rules.",
        )

        print()
        print("=" * 60)
        print("STARTING POLICY RULE EXTRACTION")
        print("=" * 60)

        rules_result = extract_rules(
            policy_text
        )

        with open(
            CURRENT_RULES_PATH,
            "w",
            encoding="utf-8"
        ) as rules_file:

            json.dump(
                rules_result,
                rules_file,
                indent=2,
                ensure_ascii=False
            )

        print()
        print(
            f"Rules saved to: "
            f"{CURRENT_RULES_PATH}"
        )

        rule_count = len(
            rules_result.get("rules", [])
        )

        # --------------------------------------------------
        # RULE VALIDATION
        # --------------------------------------------------

        update_policy_job(
            job_id,
            current_step="Rule Validation",
            progress=35,
            message=(
                f"Validated {rule_count} extracted "
                "PII, SPII and CPII rules."
            ),
        )

        # --------------------------------------------------
        # RULES EXCEL
        # --------------------------------------------------

        update_policy_job(
            job_id,
            current_step="Rules Excel",
            progress=42,
            message="Saving the extracted rules Excel workbook.",
        )

        rules_excel_path = (
            BASE_DIR
            / "extracted_text"
            / "rules.xlsx"
        )

        if not rules_excel_path.exists():

            raise RuntimeError(
                "Rules Excel file was not generated."
            )

        # --------------------------------------------------
        # GENERATE REGO POLICY
        # --------------------------------------------------

        update_policy_job(
            job_id,
            current_step="Rego Generation",
            progress=50,
            message="Generating the executable Rego policy.",
        )

        print()
        print("=" * 60)
        print("GENERATING REGO POLICY")
        print("=" * 60)

        extracted_rules = load_rules()

        rego_policy = generate_rego(
            extracted_rules
        )

        save_rego(
            rego_policy
        )

        print(
            "Rego policy generated successfully."
        )

        # --------------------------------------------------
        # POLICY RESULTS EXCEL
        # --------------------------------------------------

        update_policy_job(
            job_id,
            current_step="Policy Results Excel",
            progress=62,
            message="Saving policy rule outcomes to Excel.",
        )

        save_policy_results_excel(
            extracted_rules
        )

        policy_results_excel_path = (
            BASE_DIR
            / "policies"
            / "rego"
            / "policy_results.xlsx"
        )

        if not policy_results_excel_path.exists():

            raise RuntimeError(
                "Policy results Excel file was not generated."
            )

        # --------------------------------------------------
        # OPA DATASET EVALUATION
        # --------------------------------------------------

        update_policy_job(
            job_id,
            current_step="OPA Evaluation",
            progress=70,
            message="Evaluating the synthetic dataset with OPA.",
        )

        print()
        print("=" * 60)
        print("STARTING OPA DATASET EVALUATION")
        print("=" * 60)

        dataframe = load_dataset()

        validate_dataset_columns(
            dataframe
        )

        evaluation_results = evaluate_dataset(
            dataframe
        )

        summary = calculate_summary(
            evaluation_results
        )

        # --------------------------------------------------
        # RESULTS JSON + EXCEL
        # --------------------------------------------------

        update_policy_job(
            job_id,
            current_step="Results Excel",
            progress=88,
            message="Saving evaluation results to JSON and Excel.",
        )

        save_results(
            evaluation_results,
            summary
        )

        save_results_excel(
            evaluation_results,
            summary
        )

        results_excel_path = (
            BASE_DIR
            / "evaluation_results"
            / "results.xlsx"
        )

        if not results_excel_path.exists():

            raise RuntimeError(
                "Evaluation results Excel file was not generated."
            )

        # --------------------------------------------------
        # DATABASE HISTORY
        # --------------------------------------------------

        run_id = save_run(
            records=evaluation_results,
            dataset_name="synthetic_dataset.xlsx",
            policy_name=original_filename,
        )

        # --------------------------------------------------
        # DASHBOARD SUMMARY EXCEL
        # --------------------------------------------------

        RESULTS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        dashboard_summary_dataframe = pd.DataFrame(
            [
                {
                    "Metric": "Run ID",
                    "Value": run_id,
                },
                {
                    "Metric": "Policy",
                    "Value": original_filename,
                },
                {
                    "Metric": "Dataset",
                    "Value": "synthetic_dataset.xlsx",
                },
                {
                    "Metric": "Total Records",
                    "Value": summary["total_records"],
                },
                {
                    "Metric": "PASS",
                    "Value": summary["pass"],
                },
                {
                    "Metric": "FLAG",
                    "Value": summary["flag"],
                },
                {
                    "Metric": "BLOCK",
                    "Value": summary["block"],
                },
                {
                    "Metric": "Pass Rate",
                    "Value": f'{summary["pass_rate"]}%',
                },
            ]
        )

        with pd.ExcelWriter(
            DASHBOARD_SUMMARY_EXCEL_PATH,
            engine="openpyxl",
        ) as writer:

            dashboard_summary_dataframe.to_excel(
                writer,
                sheet_name="Dashboard Summary",
                index=False,
            )

            worksheet = writer.sheets["Dashboard Summary"]
            worksheet.freeze_panes = "A2"
            worksheet.column_dimensions["A"].width = 22
            worksheet.column_dimensions["B"].width = 34

            for cell in worksheet[1]:
                cell.font = cell.font.copy(bold=True)
                cell.alignment = cell.alignment.copy(
                    horizontal="center",
                    vertical="center",
                )

            for row in worksheet.iter_rows(min_row=2):
                for cell in row:
                    cell.alignment = cell.alignment.copy(
                        vertical="top",
                    )

        print(
            f"Dashboard summary Excel saved to: "
            f"{DASHBOARD_SUMMARY_EXCEL_PATH}"
        )

        # --------------------------------------------------
        # STORE ALL RUN ARTIFACTS
        # --------------------------------------------------

        run_artifacts = {
            "policy_pdf": CURRENT_POLICY_PATH,
            "policy_excel": policy_results_excel_path,
            "policy_text": POLICY_TEXT_TXT_PATH,
            "rules_json": CURRENT_RULES_PATH,
            "rules_excel": rules_excel_path,
            "rego": (
                BASE_DIR
                / "policies"
                / "rego"
                / "policy.rego"
            ),
            "results_json": RESULTS_PATH,
            "results_excel": results_excel_path,
            "dashboard_summary_excel": DASHBOARD_SUMMARY_EXCEL_PATH,
        }

        artifact_paths = upload_run_artifacts(
            run_id=run_id,
            artifacts=run_artifacts,
            original_policy_filename=original_filename,
        )

        update_run_artifact_paths(
            run_id=run_id,
            artifact_paths=artifact_paths,
        )

        # --------------------------------------------------
        # COMPLETE
        # --------------------------------------------------

        print()
        print("=" * 60)
        print("POLICY PROCESSING COMPLETE")
        print("=" * 60)

        print(
            f"Uploaded file : {original_filename}"
        )

        print(
            f"Pages         : {len(pages)}"
        )

        print(
            f"Rules         : {rule_count}"
        )

        print(
            f"PASS          : {summary['pass']}"
        )

        print(
            f"FLAG          : {summary['flag']}"
        )

        print(
            f"BLOCK         : {summary['block']}"
        )

        print(
            f"Pass rate     : "
            f"{summary['pass_rate']}%"
        )

        result = {
            "success": True,
            "message": (
                "Policy processed successfully."
            ),
            "filename": original_filename,
            "page_count": len(pages),
            "rule_count": rule_count,
            "policy_file": str(
                CURRENT_POLICY_PATH
            ),
            "extracted_text_file": str(
                POLICY_TEXT_TXT_PATH
            ),
            "rules_file": str(
                CURRENT_RULES_PATH
            ),
            "dashboard_summary_excel": str(
                DASHBOARD_SUMMARY_EXCEL_PATH
            ),
            "evaluation": {
                "total_records":
                    summary["total_records"],
                "pass":
                    summary["pass"],
                "flag":
                    summary["flag"],
                "block":
                    summary["block"],
                "pass_rate":
                    summary["pass_rate"],
            },
            "run_id": run_id,
            "rules": rules_result["rules"]
        }

        update_policy_job(
            job_id,
            status="completed",
            current_step="Dashboard Ready",
            progress=100,
            message="Policy evaluation completed successfully.",
            result=result,
        )

    except Exception as error:

        print()
        print("=" * 60)
        print("POLICY PROCESSING FAILED")
        print("=" * 60)

        print(
            f"Error: {error}"
        )

        update_policy_job(
            job_id,
            status="failed",
            current_step="Processing Failed",
            progress=100,
            message=str(error),
            result={
                "success": False,
                "message": str(error),
            },
        )

@app.post("/upload-policy")
async def upload_policy(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):

    print()
    print("=" * 60)
    print("POLICY UPLOAD REQUEST RECEIVED")
    print("=" * 60)

    print(
        f"Filename     : {file.filename}"
    )

    print(
        f"Content type : {file.content_type}"
    )
    
    global CURRENT_POLICY_ORIGINAL_FILENAME
    CURRENT_POLICY_ORIGINAL_FILENAME = file.filename

    # --------------------------------------------------
    # VALIDATE PDF
    # --------------------------------------------------

    if file.content_type != "application/pdf":

        print(
            "ERROR: Uploaded file is not a PDF."
        )

        return {
            "success": False,
            "message": (
                "Only PDF files are supported."
            )
        }

    # --------------------------------------------------
    # REMOVE PREVIOUS POLICY
    # --------------------------------------------------

    delete_previous_policy()

    # --------------------------------------------------
    # READ + SAVE UPLOADED PDF
    # --------------------------------------------------

    file_contents = await file.read()

    with open(
        CURRENT_POLICY_PATH,
        "wb"
    ) as output_file:

        output_file.write(
            file_contents
        )

    print(
        f"PDF saved to : "
        f"{CURRENT_POLICY_PATH}"
    )

    # --------------------------------------------------
    # CREATE PROCESSING JOB
    # --------------------------------------------------

    import uuid

    job_id = str(
        uuid.uuid4()
    )

    POLICY_JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "current_step": "Queued",
        "progress": 0,
        "message": (
            "Policy uploaded. "
            "Processing will begin shortly."
        ),
        "result": None,
    }

    background_tasks.add_task(
        process_policy_upload,
        job_id,
        file.filename,
    )

    return {
        "success": True,
        "message": (
            "Policy uploaded and "
            "processing started."
        ),
        "job_id": job_id,
        "status": "queued",
    }


@app.get("/upload-status/{job_id}")
def get_upload_status(
    job_id: str,
):

    job = POLICY_JOBS.get(
        job_id
    )

    if job is None:

        raise HTTPException(
            status_code=404,
            detail="Policy processing job not found."
        )

    return job


# --------------------------------------------------
# Evaluation History
# --------------------------------------------------

@app.get("/api/runs")
def api_get_runs():
    return get_runs()

# --------------------------------------------------
# Get Evaluation Run
# --------------------------------------------------

@app.get("/api/runs/{run_id}")
def api_get_run(run_id: int):
    run = get_run(run_id)

    if run is None:
        return {
            "success": False,
            "message": "Evaluation run not found."
        }

    return run

@app.get("/api/runs/{run_id}/artifact/{artifact_name}")
def download_run_artifact(
    run_id: int,
    artifact_name: str,
):

    allowed_artifacts = {
        "policy_pdf",
        "policy_excel",
        "policy_text",
        "rules_json",
        "rules_excel",
        "rego",
        "results_json",
        "results_excel",
        "dashboard_summary_excel",
    }

    if artifact_name not in allowed_artifacts:

        raise HTTPException(
            status_code=400,
            detail="Invalid artifact name."
        )

    run = get_run(
        run_id
    )

    if run is None:

        raise HTTPException(
            status_code=404,
            detail="Evaluation run not found."
        )

    artifact_paths = run.get(
        "artifact_paths"
    ) or {}

    storage_path = artifact_paths.get(
        artifact_name
    )

    if not storage_path:

        raise HTTPException(
            status_code=404,
            detail=(
                f"{artifact_name} is not available "
                "for this run."
            )
        )

    signed_url = create_run_artifact_url(
        storage_path
    )

    return RedirectResponse(
        url=signed_url
    )

@app.get("/download-synthetic-data")
def download_synthetic_data():
    file_path = BASE_DIR / "synthetic_data" / "synthetic_dataset.xlsx"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Synthetic dataset not found."
        )

    return FileResponse(
        path=file_path,
        filename="synthetic_dataset.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    
@app.get("/download-results-excel")
def download_results_excel():
    results_excel_path = (
        BASE_DIR
        / "evaluation_results"
        / "results.xlsx"
    )

    if not results_excel_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Results Excel file not found."
        )

    return FileResponse(
        path=results_excel_path,
        filename="results.xlsx",
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
    
@app.get("/download-policy-text")
def download_policy_text():
    policy_text_path = (
        BASE_DIR
        / "extracted_text"
        / "policy.txt"
    )

    if not policy_text_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Policy text file not found."
        )

    return FileResponse(
        path=policy_text_path,
        filename="policy.txt",
        media_type="text/plain",
    )


@app.get("/download-rules-excel")
def download_rules_excel():
    rules_excel_path = (
        BASE_DIR
        / "extracted_text"
        / "rules.xlsx"
    )

    if not rules_excel_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Rules Excel file not found."
        )

    return FileResponse(
        path=rules_excel_path,
        filename="rules.xlsx",
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


@app.get("/download-dashboard-summary-excel")
def download_dashboard_summary_excel():
    dashboard_summary_path = (
        BASE_DIR
        / "evaluation_results"
        / "dashboard_summary.xlsx"
    )

    if not dashboard_summary_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Dashboard summary Excel file not found."
        )

    return FileResponse(
        path=dashboard_summary_path,
        filename="dashboard_summary.xlsx",
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


@app.get("/download-policy-pdf")
def download_policy_pdf():
    policy_pdf_path = (
        BASE_DIR
        / "policies"
        / "current_policy.pdf"
    )

    if not policy_pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Current policy PDF not found."
        )

    return FileResponse(
        path=policy_pdf_path,
        filename=CURRENT_POLICY_ORIGINAL_FILENAME,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{CURRENT_POLICY_ORIGINAL_FILENAME}"'
            )
        },
    )


@app.get("/download-policy-results-excel")
def download_policy_results_excel():
    policy_results_excel_path = (
        BASE_DIR
        / "policies"
        / "rego"
        / "policy_results.xlsx"
    )

    if not policy_results_excel_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Policy results Excel file not found."
        )

    return FileResponse(
        path=policy_results_excel_path,
        filename="policy_results.xlsx",
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )