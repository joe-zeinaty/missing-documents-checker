from datetime import datetime

from flask import Flask, render_template, request

# Import the modules used to validate inputs and generate comparison outputs.
from client_parser import parse_clients
from document_checker import inspect_documents, build_client_report
from report_export import build_missing_report_download
from reminder_builder import build_reminders

# Create the web application and limit the entire upload request to 25 MiB.
# Requests exceeding this limit are handled by upload_too_large().
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# Display the upload form on GET and process a submitted comparison on POST.
@app.route("/", methods=["GET", "POST"])
def home():
    # Set the default reporting month and initialize request-specific results.
    month = "2026-08"
    error = None
    upload_summary = None
    file_results = []
    client_report = []
    missing_report_download = None
    reminders = []

    if request.method == "POST":
        # Read the selected month and client register from the submitted form.
        month = request.form.get("month", "")
        clients_file = request.files.get("clients")

        # Collect document uploads, excluding entries with no filename.
        # This does not check whether a selected file has empty contents.
        documents = [
            file
            for file in request.files.getlist("documents")
            if file.filename
        ]

        # Require a client register before starting the comparison.
        if not clients_file or not clients_file.filename:
            error = "Please upload your client CSV."

        # Check the CSV extension; parse_clients() validates its contents.
        elif not clients_file.filename.lower().endswith(".csv"):
            error = "The client list must be a CSV file."

        else:
            # Validate the reporting month independently of browser controls.
            try:
                parsed_month = datetime.strptime(month, "%Y-%m")

                # Require YYYY-MM, including a two-digit month.
                if parsed_month.strftime("%Y-%m") != month:
                    raise ValueError

            except ValueError:
                error = "Please choose a valid reporting month."

        # Run the comparison only after the initial input checks succeed.
        if error is None:
            try:
                # Read and validate the CSV, returning structured client records.
                clients = parse_clients(clients_file)

                # Summarize the accepted register and submitted document count.
                upload_summary = {
                    "clients_filename": clients_file.filename,
                    "client_count": len(clients),
                    "document_count": len(documents),
                    "month": month,
                }

                # Interpret filenames across all months and flag exceptions,
                # unknown clients and repeated submissions. PDF contents are
                # not inspected, and original filenames are not changed.
                file_results = inspect_documents(documents, clients)

                # Compare client requirements against the selected month's
                # recognized files while preserving the complete filename audit.
                client_report = build_client_report(
                    clients, file_results, month
                )

                # Generate the missing-document CSV from the monthly report.
                missing_report_download = build_missing_report_download(
                    client_report, month
                )

                # Generate copy-only drafts for clients with missing documents.
                # This function does not send email.
                reminders = build_reminders(client_report, month)

            except ValueError as validation_error:
                # Display validation errors raised during comparison processing.
                error = str(validation_error)

    # Render the form, messages, monthly report, download, drafts and file audit.
    return render_template(
        "index.html",
        month=month,
        error=error,
        upload_summary=upload_summary,
        file_results=file_results,
        client_report=client_report,
        missing_report_download=missing_report_download,
        reminders=reminders,
    )


# Return the form with empty results and HTTP 413 when an upload is too large.
@app.errorhandler(413)
def upload_too_large(error):
    return render_template(
        "index.html",
        month="2026-08",
        error="The total upload exceeds 25 MB. Please select fewer files.",
        upload_summary=None,
        file_results=[],
        client_report=[],
        missing_report_download=None,
        reminders=[],
    ), 413


# Run Flask's development server locally. Gunicorn imports the app on Render,
# so this block does not execute in the deployed service.
if __name__ == "__main__":
    app.run()
