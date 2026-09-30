from datetime import datetime


# Convert internal document codes into client-friendly descriptions.
DOCUMENT_LABELS = {
    "bank": "Bank statements",
    "invoices_in": "Purchase invoices",
    "invoices_out": "Sales invoices",
    "payroll": "Payroll records",
}


def build_reminders(client_report, month):
    """Create one reminder draft per client with missing documents."""

    # Turn the validated reporting month into a readable email date.
    # Example: 2026-08 becomes August 2026 on an English-language server.
    month_label = datetime.strptime(month, "%Y-%m").strftime("%B %Y")

    reminders = []

    for client in client_report:
        # Complete clients do not need a reminder.
        if not client["missing_documents"]:
            continue

        # List only the requirements marked missing in the client report.
        document_list = "\n".join(
            f"- {DOCUMENT_LABELS[document]}"
            for document in client["missing_documents"]
        )

        subject = f"Outstanding documents for {month_label}"

        # Use a polite, practical tone without inventing a filing deadline.
        # The advisor replaces the signature placeholders after copying.
        body = (
            f"Dear {client['name']},\n\n"
            f"As we prepare your accounts for {month_label}, "
            "our records show that we are still awaiting "
            "the following documents:\n\n"
            f"{document_list}\n\n"
            "Please send these at your earliest convenience so we can "
            "complete our review. If you have already provided them, "
            "please let us know when they were sent so we can "
            "check our records.\n\n"
            "If any item does not apply for this month, "
            "please confirm this by reply.\n\n"
            "Thank you for your assistance.\n\n"
            "Kind regards,\n"
            "[Advisor name]\n"
            "[Firm name]"
        )

        # Return plain text for display. There is no email-sending operation.
        reminders.append({
            "client_id": client["client_id"],
            "name": client["name"],
            "email": client["email"],
            "subject": subject,
            "body": body,
        })

    return reminders