import csv
import io
import re


# The CSV must contain these four columns.
EXPECTED_COLUMNS = {
    "client_id",
    "name",
    "email",
    "required_documents",
}

# These are the only document categories the application understands.
DOCUMENT_CODES = {
    "bank",
    "invoices_in",
    "invoices_out",
    "payroll",
}


def parse_clients(upload):
    """Validate an uploaded CSV and return a list of client dictionaries."""

    # Limit the client register to 1 MB.
    # Reading one extra byte lets us detect an oversized file.
    max_size = 1024 * 1024
    raw_data = upload.read(max_size + 1)

    if len(raw_data) > max_size:
        raise ValueError("The client CSV must be 1 MB or smaller.")

    # utf-8-sig also handles the BOM added by Excel's UTF-8 CSV export.
    try:
        content = raw_data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Please save the client CSV using UTF-8 encoding.")

    # DictReader uses column headers as dictionary keys.
    # strict=True detects certain malformed CSV structures.
    reader = csv.DictReader(io.StringIO(content, newline=""), strict=True)

    clients = []
    seen_ids = set()

    try:
        # Require exactly the expected headers, in any order.
        headers = reader.fieldnames
        if (
            headers is None
            or len(headers) != len(EXPECTED_COLUMNS)
            or set(headers) != EXPECTED_COLUMNS
        ):
            raise ValueError(
                "CSV headers must be: "
                "client_id,name,email,required_documents"
            )

        for row in reader:
            line = reader.line_num

            # Extra values produce a None key; missing values produce
            # None values. Neither should be silently accepted.
            if None in row or any(value is None for value in row.values()):
                raise ValueError(
                    f"CSV line {line}: incorrect number of columns."
                )

            # Remove surrounding spaces while keeping IDs as strings.
            # This preserves leading zeros, such as '001'.
            row = {key: value.strip() for key, value in row.items()}

                        # Normalize the register's client IDs to the same format
            # used by the filename parser. Preserve all four digits.
            client_id = row["client_id"].upper()

            # Require capital K followed by exactly four ASCII digits.
            # Examples: K1040 and K0007 are valid; K104 and X1040 are not.
            if not re.fullmatch(r"K[0-9]{4}", client_id):
                raise ValueError(
                    f"CSV line {line}: client ID must be K followed "
                    "by exactly four digits, for example K1040."
                )

            # Store the normalized ID for tables, exports and reminders.
            row["client_id"] = client_id

            # Treat casing differences as the same client ID.
            id_key = client_id.casefold()
            if id_key in seen_ids:
                raise ValueError(
                    f"CSV line {line}: duplicate client ID '{client_id}'."
                )
            seen_ids.add(id_key)

            # Require contact information for the later reminder drafts.
            # This checks presence, not whether an email address exists.
            if not row["name"] or not row["email"]:
                raise ValueError(
                    f"CSV line {line}: name and email are required."
                )

            # Convert the semicolon-separated field into a Python list.
            # Ignore empty entries and normalize code capitalization.
            documents = [
                code.strip().lower()
                for code in row["required_documents"].split(";")
                if code.strip()
            ]

            if not documents:
                raise ValueError(
                    f"CSV line {line}: specify at least one required document."
                )

            # Reject unknown codes so spelling mistakes cannot hide
            # a document requirement.
            unknown_codes = set(documents) - DOCUMENT_CODES
            if unknown_codes:
                raise ValueError(
                    f"CSV line {line}: unknown document codes: "
                    f"{', '.join(sorted(unknown_codes))}."
                )

            # Remove repeated requirements while preserving their order.
            row["required_documents"] = list(dict.fromkeys(documents))
            clients.append(row)

    except csv.Error as error:
        raise ValueError(
            f"Invalid CSV formatting near line {reader.line_num}."
        ) from error

    if not clients:
        raise ValueError("The CSV contains no client records.")

    return clients