import os
import json
from pathlib import Path
import pandas as pd
import pytest
import logging
import subprocess
from typing import Dict, List

logger = logging.getLogger(__name__)

# Long timeout needed because pipeline includes PDF generation via Chromium
PIPELINE_TIMEOUT = 600  # 10 minutes
INVOICE_MONTH = "2025-06"

EXPECTED_CSV_FILES = [
    "billable 2025-06.csv",
    "nonbillable 2025-06.csv",
    "NERC-2025-06-Total-Invoice.csv",
    "BU_Internal 2025-06.csv",
    "Lenovo 2025-06.csv",
    "MOCA-A_Prepaid_Groups-2025-06-Invoice.csv",
    "NERC_Prepaid_Group-Credits-2025-06.csv",
    "OCP_TEST 2025-06.csv",
]

EXPECTED_DIRECTORIES = ["pi_invoices"]


@pytest.fixture
def project_root() -> Path:
    """Get the root directory of the project.

    Returns:
        Path: The absolute path to the project root directory.
    """
    return Path(__file__).parent.parent.parent.parent


@pytest.fixture
def test_data_dir() -> Path:
    """Get the directory containing test data files.

    Returns:
        Path: The absolute path to the test data directory.
    """
    return Path(__file__).parent / "test_data"


@pytest.fixture
def test_invoice_dir(test_data_dir) -> Path:
    """Get the directory containing test invoice files."""
    return test_data_dir / "test_invoices"


def _setup_workspace(
    test_data_dir: Path, test_invoice_dir: Path, project_root: Path, workspace: Path
):
    """Set up the workspace by collecting absolute paths to test data files.

    Args:
        test_data_dir: Path to the directory containing test data files.
        project_root: Path to the project root directory.
        workspace: Path to the temporary workspace directory.

    Returns:
        Dict[str, Path]: A dictionary mapping test file names to their absolute paths.
    """
    # Absolute paths prevent issues when running pipeline from different working directory
    test_files = {}
    for test_file in test_data_dir.glob("*"):
        test_files[test_file.name] = test_file.absolute()

    test_files["test_invoice_dir"] = test_invoice_dir.absolute()

    process_report_dir = workspace / "process_report"
    process_report_dir.mkdir(exist_ok=True)

    # Using a symlink to real institute_list.yaml file that's hardcoded in the util.py file
    institute_list_src = project_root / "process_report" / "institute_list.yaml"
    institute_list_dest = process_report_dir / "institute_list.yaml"
    institute_list_dest.symlink_to(institute_list_src)

    # Using a symlink to real templates directory that's hardcoded in the process_report.py file
    templates_src = project_root / "process_report" / "templates"
    templates_dest = process_report_dir / "templates"
    templates_dest.symlink_to(templates_src, target_is_directory=True)

    return test_files


def _prepare_pipeline_execution(
    test_files: Dict[str, Path], workspace: Path, project_root: Path
):
    """Build command and environment for pipeline execution.

    Args:
        test_files: Dictionary mapping test file names to their absolute paths.
        workspace: Path to the temporary workspace directory.
        project_root: Path to the project root directory.

    Returns:
        Tuple[List[str], Dict[str, str]]: A tuple containing the command list and
            environment dictionary for running the pipeline.
    """
    # Build command
    command = [
        "python",
        "-m",
        "process_report.process_report",
    ]

    # Environment setup for subprocess execution
    env = os.environ.copy()
    env["INVOICE_MONTH"] = INVOICE_MONTH

    # pydantic_settings parses complex types as JSON-encoded strings: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/#parsing-environment-variable-values
    env["COLDFRONT_API_FILEPATHS"] = json.dumps(
        (
            str(test_files["test_coldfront_api_data.json"]),
            str(test_files["test_supplement_api_data.yaml"]),
        )
    )
    env["FETCH_FROM_S3"] = "false"
    env["UPLOAD_TO_S3"] = "false"
    env["invoice_path_template"] = str(test_files["test_invoice_dir"])

    env["PI_REMOTE_FILEPATH"] = str(test_files["test_PI.csv"])
    env["ALIAS_REMOTE_FILEPATH"] = str(test_files["test_alias.csv"])
    env["PREPAY_DEBITS_REMOTE_FILEPATH"] = str(test_files["test_prepay_debits.csv"])

    env["PREPAY_CREDITS_FILEPATH"] = str(test_files["test_prepay_credits.csv"])
    env["PREPAY_PROJECTS_FILEPATH"] = str(test_files["test_prepay_projects.csv"])
    env["PREPAY_CONTACTS_FILEPATH"] = str(test_files["test_prepay_contacts.csv"])
    env["nonbillable_pis_filepath"] = str(test_files["test_pi.yaml"])
    env["nonbillable_projects_filepath"] = str(test_files["test_projects.yaml"])

    # Fallback ensures test works even when CI environment doesn't set Chrome path
    env.setdefault("CHROME_BIN_PATH", "/usr/bin/chromium")
    env["PYTHONPATH"] = str(project_root) + ":" + env.get("PYTHONPATH", "")

    return command, env


def _run_pipeline(command: List[str], env: Dict[str, str], workspace: Path):
    """Run the pipeline and return the result.

    Args:
        command: List of command arguments to execute the pipeline.
        env: Environment variables dictionary.
        workspace: Path to the temporary workspace directory where the pipeline will run.

    Returns:
        subprocess.CompletedProcess: The result of the pipeline execution.

    Raises:
        pytest.fail: If the pipeline execution times out.
    """
    logger.info(f"Running pipeline in: {workspace}")

    try:
        result = subprocess.run(
            command,
            env=env,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=PIPELINE_TIMEOUT,
        )

        if result.stderr:
            logger.warning(f"Pipeline stderr: {result.stderr}")

        return result

    except subprocess.TimeoutExpired:
        pytest.fail(f"Pipeline execution timed out after {PIPELINE_TIMEOUT} seconds")


def _validate_outputs(workspace: Path) -> None:
    """Validate all expected pipeline outputs.

    Args:
        workspace: Path to the temporary workspace directory containing pipeline outputs.

    Raises:
        AssertionError: If any expected output file is missing, empty, or invalid.
        pytest.fail: If CSV files cannot be read or parsed.
    """
    logger.info(f"Validating pipeline outputs in: {workspace}")

    for csv_file in EXPECTED_CSV_FILES:
        csv_path = workspace / csv_file
        assert csv_path.exists(), f"CSV file not found: {csv_path}"
        assert csv_path.is_file(), f"Path is not a file: {csv_path}"
        assert csv_path.stat().st_size > 0, f"CSV file is empty: {csv_path}"

        try:
            df = pd.read_csv(csv_path)
            assert len(df.columns) > 0, f"CSV has no columns: {csv_path}"
        except Exception as e:
            pytest.fail(f"Failed to read CSV {csv_path}: {e}")

    # Validate that only expected CSV files are created (no more, no less)
    actual_csv_files = set(csv_path.name for csv_path in workspace.glob("*.csv"))
    expected_csv_files = set(EXPECTED_CSV_FILES)

    unexpected_files = actual_csv_files - expected_csv_files
    if unexpected_files:
        pytest.fail(f"Unexpected CSV files created: {sorted(unexpected_files)}")

    missing_files = expected_csv_files - actual_csv_files
    if missing_files:
        pytest.fail(f"Expected CSV files missing: {sorted(missing_files)}")

    # PI invoices are generated as PDFs in separate directory structure
    pi_dir = workspace / "pi_invoices"
    assert pi_dir.exists(), f"PI invoices directory not found: {pi_dir}"
    assert pi_dir.is_dir(), f"PI invoices path is not a directory: {pi_dir}"

    pdf_files = list(pi_dir.glob("*.pdf"))
    assert len(pdf_files) > 0, f"No PDF files found in {pi_dir}"

    logger.info("All pipeline outputs validated successfully")


def test_e2e_pipeline_execution(
    project_root: Path, test_data_dir: Path, test_invoice_dir: Path, tmp_path: Path
):
    """
    Validates the full pipeline runs without errors and produces expected outputs.

    This test ensures integration between all components rather than testing edge cases.
    """
    workspace = tmp_path

    test_files = _setup_workspace(
        test_data_dir, test_invoice_dir, project_root, workspace
    )

    command, env = _prepare_pipeline_execution(test_files, workspace, project_root)

    result = _run_pipeline(command, env, workspace)

    assert result.returncode == 0, (
        f"Pipeline failed with exit code {result.returncode}\n"
        f"Stdout: {result.stdout}\n"
        f"Stderr: {result.stderr}"
    )

    _validate_outputs(workspace)
