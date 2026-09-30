import re
from pathlib import PurePosixPath


# Map English month names and abbreviations without depending on
# the operating system's language settings.
MONTH_NAMES = (
    "january", "february", "march", "april",
    "may", "june", "july", "august",
    "september", "october", "november", "december",
)

MONTH_NUMBERS = {}

for number, name in enumerate(MONTH_NAMES, start=1):
    MONTH_NUMBERS[name] = number
    MONTH_NUMBERS[name[:3]] = number


def normalize_month(value):
    """Convert a supported filename date into YYYY-MM."""

    # Treat spaces, underscores, dots and hyphens as date separators.
    value = re.sub(r"[\s_.-]+", "-", value.strip().lower())

    # Accept year-first numeric dates, such as 2026-08.
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)

    if match:
        year, month = map(int, match.groups())
    else:
        # Accept month-first numeric dates, such as 08-2026.
        match = re.fullmatch(r"(\d{2})-(\d{4})", value)

        if match:
            month, year = map(int, match.groups())
        else:
            # Accept English month names, with or without a separator:
            # Aug2026, Aug-2026, or August_2026.
            match = re.fullmatch(r"([a-z]+)-?(\d{4})", value)

            if not match or match.group(1) not in MONTH_NUMBERS:
                raise ValueError("Unrecognized date format.")

            month = MONTH_NUMBERS[match.group(1)]
            year = int(match.group(2))

    # Reject impossible months and year zero.
    if not 1 <= month <= 12 or not 1 <= year <= 9999:
        raise ValueError("Invalid year or month.")

    return f"{year:04d}-{month:02d}"


def parse_filename(filename):
    """Extract a client ID, document type and month from a filename."""

    # Keep only the filename if a browser supplies path components.
    # Handle both Windows and Unix-style separators.
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1]

    # Separate the extension so it is not interpreted as part of the date.
    extension = PurePosixPath(basename).suffix.lower()

        
    if not extension:
        raise ValueError("The filename has no extension.")

    # Accept PDF documents only. The extension was already lowercased,
    # so both .pdf and .PDF are accepted.
    # Files ending in .pdf.tmp are rejected because their extension is .tmp.
    if extension != ".pdf":
        raise ValueError("Unsupported file type — PDF required.")

    stem = basename[:-len(extension)]

    # Ignore a trailing Windows copy suffix, such as ' (1)'.
    # This allows matching; it does not prove that file contents match.
    stem = re.sub(r"\s*\(\d+\)$", "", stem).strip()

    # Require K followed by exactly four digits.
    # Accept casing and separator variations in the document category.
    # fullmatch prevents silently ignoring extra text in the filename.
    match = re.fullmatch(
        r"(?P<client>k\d{4})"
        r"[\s_.-]+"
        r"(?P<document>bank|invoices[\s_.-]*in|"
        r"invoices[\s_.-]*out|payroll)"
        r"[\s_.-]+"
        r"(?P<month>.+)",
        stem,
        flags=re.IGNORECASE | re.ASCII,
    )

    if not match:
        raise ValueError(
            "Expected K followed by four digits, "
            "a recognized document type, and a month."
        )

    # Convert document variants into the codes used by clients.csv.
    document_key = re.sub(
        r"[\s_.-]+", "", match.group("document").lower()
    )

    document_codes = {
        "bank": "bank",
        "invoicesin": "invoices_in",
        "invoicesout": "invoices_out",
        "payroll": "payroll",
    }

    client_id = match.group("client").upper()
    document = document_codes[document_key]
    month = normalize_month(match.group("month"))

    # Return structured data for the later comparison step.
    # No original file is renamed or modified here.
    return {
        "original_filename": basename,
        "client_id": client_id,
        "document": document,
        "month": month,
        "normalized_filename": (
            f"{client_id}_{document}_{month}{extension}"
        ),
    }