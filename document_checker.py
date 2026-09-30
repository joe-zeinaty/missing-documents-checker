from filename_parser import parse_filename


def inspect_documents(documents, clients):
    """Validate filename assignments and flag repeated document keys."""

    # Match client IDs without regard to capitalization.
    # The CSV parser already rejects case-insensitive duplicate IDs.
    known_client_ids = {
        client["client_id"].upper()
        for client in clients
    }

    # Remember the first filename for each client/type/month combination.
    # Including the month keeps July and August requirements separate.
    first_submission = {}

    # Keep one audit row per upload, including rejected and repeated names.
    results = []

    for uploaded_file in documents:
        try:
            result = parse_filename(uploaded_file.filename)

        except ValueError as filename_error:
            # Keep unrecognized filenames visible without stopping the batch.
            results.append({
                "original_filename": uploaded_file.filename,
                "normalized_filename": "",
                "client_id": "",
                "document": "",
                "month": "",
                "status": "Needs review",
                "message": str(filename_error),
            })
            continue

        # A correctly formatted ID must also exist in the client register.
        # Unknown clients cannot satisfy any registered client's requirement.
        if result["client_id"] not in known_client_ids:
            result["status"] = "Unknown client"
            result["message"] = "Client ID was not found in clients.csv."
            results.append(result)
            continue

        # This key represents one document category for one client/month.
        # Extensions and naming variations do not create extra requirements.
        document_key = (
            result["client_id"],
            result["document"],
            result["month"],
        )

        if document_key in first_submission:
            # Flag additional submissions for the same requirement.
            # Original files remain unchanged; nothing is deleted.
            result["status"] = "Repeated submission"
            result["message"] = (
                "Same client, document type and month as: "
                f"{first_submission[document_key]}"
            )
        else:
            # Record the first recognized submission for this requirement.
            first_submission[document_key] = result["original_filename"]
            result["status"] = "Recognized"
            result["message"] = ""

        results.append(result)

    return results

def build_client_report(clients, file_results, selected_month):
    """Compare each client's requirements with the selected month's files."""

    # Keep a consistent column order for the report.
    document_codes = (
        "bank",
        "invoices_in",
        "invoices_out",
        "payroll",
    )

    # Store each recognized client/document combination once.
    # Files for other months remain in the audit but do not satisfy
    # this month's requirements.
    delivered_documents = {
        (file["client_id"], file["document"])
        for file in file_results
        if file["status"] == "Recognized"
        and file["month"] == selected_month
    }

    report = []

    # Iterate over the CSV clients, including those with no uploads.
    for client in clients:
        client_id = client["client_id"].upper()
        required_documents = set(client["required_documents"])

        document_statuses = {}
        missing_documents = []

        for document in document_codes:
            # Check requirements first: an unsolicited file does not
            # turn a non-required category into a required category.
            if document not in required_documents:
                status = "Not required"

            elif (client_id, document) in delivered_documents:
                status = "Delivered"

            else:
                status = "Missing"
                missing_documents.append(document)

            document_statuses[document] = status

        # Preserve contact details for the later CSV export and reminders.
        report.append({
            "client_id": client_id,
            "name": client["name"],
            "email": client["email"],
            "documents": document_statuses,
            "missing_documents": missing_documents,
            "missing_count": len(missing_documents),
        })

    return report