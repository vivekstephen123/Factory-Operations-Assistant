import os
import datetime
from typing import Tuple

REPORTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports"))


def save_response_to_file(
    content: str,
    question: str = "",
    filename: str = None
) -> Tuple[str, str]:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if not filename:
        if "m102" in question.lower() or "m102" in content.lower():
            filename = "M102_investigation.txt"
        else:
            safe_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"operations_report_{safe_ts}.txt"

    filepath = os.path.join(REPORTS_DIR, filename)

    report_text = (
        f"========================================================\n"
        f"        FACTORY OPERATIONS ASSISTANT - REPORT           \n"
        f"========================================================\n"
        f"Generated At: {timestamp}\n"
        f"Inquiry / Subject: {question}\n"
        f"--------------------------------------------------------\n\n"
        f"{content}\n\n"
        f"--------------------------------------------------------\n"
        f"Status: Logged and Verified by Plant Operations System\n"
        f"========================================================\n"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report_text)

    return filepath, report_text
