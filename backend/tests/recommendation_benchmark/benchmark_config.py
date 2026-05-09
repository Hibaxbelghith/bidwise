from pathlib import Path


DATASET_DIR = Path(__file__).resolve().parent
PROFILES_PATH = DATASET_DIR / "profiles" / "profiles.json"
RESUMES_PATH = DATASET_DIR / "resumes" / "resumes.json"
EXPECTED_RESULTS_PATH = DATASET_DIR / "expected" / "expected_results.json"
OPPORTUNITIES_PATH = DATASET_DIR / "expected" / "opportunities.json"

BENCHMARK_REPORT_DIR = DATASET_DIR.parents[1] / "benchmark_reports"
DEFAULT_TOP_K = 10
PRECISION_GOOD_THRESHOLD = 0.70
PRECISION_MEDIUM_THRESHOLD = 0.45

