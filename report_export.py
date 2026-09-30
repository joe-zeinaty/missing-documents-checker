import base64
import csv
import io


def safe_csv_value(value):
    """Prevent user-provided values from becoming spreadsheet formulas."""

    text = str(value)

    # Spreadsheet applications may interpret these prefixes as formulas.
    # A leading apostrophe makes the exported value plain text.
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text

    return text


def build_missing_report_download(client_report, month):
    """Create a CSV and encode it for a browser download link."""

    # Build the CSV in memory without saving client data on the server.
    output = io.StringIO(newline="")
    writer = csv.writer(output)

    # Always include headers, even when no documents are missing.
    writer.writerow([
        "client_id",
        "name",
        "email",
        "document",
        "month",
    ])

    for client in client_report:
        # A client missing three categories produces three report rows.
        # Clients with no missing documents produce no report rows.
        for document in client["missing_documents"]:
            row = [
                client["client_id"],
                client["name"],
                client["email"],
                document,
                month,
            ]

            # csv.writer handles commas, quotes and line breaks in values.
            writer.writerow([safe_csv_value(value) for value in row])

    # UTF-8 with a BOM helps Excel display accented names correctly.
    csv_bytes = output.getvalue().encode("utf-8-sig")

    # Base64 lets us embed this small report in an HTML download link.
    # This is encoding, not encryption.
    return base64.b64encode(csv_bytes).decode("ascii")