from datetime import datetime

from flask import Flask, render_template, request

from client_parser import parse_clients

# Inspect uploaded filenames and build the monthly client comparison.
from document_checker import inspect_documents, build_client_report

# Generate the missing-document CSV from the monthly client results.
from report_export import build_missing_report_download

# Build copy-only reminder drafts from the monthly comparison.
from reminder_builder import build_reminders

# Create the Flask application.
app = Flask(__name__)

# Limit each complete upload request (CSV + documents) to 25 MB.
# Flask returns an HTTP 413 error if this limit is exceeded.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# GET displays the form.
# POST handles the files and month submitted through the form.
@app.route("/", methods=["GET", "POST"])
def home():
    # Initial values for the form and its results.
    month = "2026-08"
    error = None
    upload_summary = None
    file_results = []
    client_report = []
    missing_report_download = None
    reminders = []

    if request.method == "POST":
        # Retrieve the reporting month using the input's name="month".
        # Use an empty string if the field is missing.
        month = request.form.get("month", "")

        # Retrieve the single client CSV using name="clients".
        clients_file = request.files.get("clients")

        # Retrieve all uploads from name="documents".
        # Ignore empty entries produced when no document was selected.
        documents = [
            file
            for file in request.files.getlist("documents")
            if file.filename
        ]

        # Check that the user supplied a client list.
        if not clients_file or not clients_file.filename:
            error = "Please upload your client CSV."

        # Check the filename extension, ignoring capitalization.
        # This does not validate the CSV's contents; that comes later.
        elif not clients_file.filename.lower().endswith(".csv"):
            error = "The client list must be a CSV file."

        else:
            # Validate the month on the server, even though the browser
            # provides a month picker. Browser inputs can be bypassed.
            try:
                parsed_month = datetime.strptime(month, "%Y-%m")

                # Require the exact YYYY-MM format, including a
                # leading zero for single-digit months.
                if parsed_month.strftime("%Y-%m") != month:
                    raise ValueError

            except ValueError:
                error = "Please choose a valid reporting month."

        # Build a confirmation only if all checks passed.
        # For now, we receive the uploads without parsing their contents,
        # matching filenames, or deliberately saving them to a folder.
                # Parse the register only after the file and month checks pass.
                # Validate the client register before processing document names.
                # Process documents only after the initial form checks pass.
        if error is None:
            try:
                clients = parse_clients(clients_file)

                upload_summary = {
                    "clients_filename": clients_file.filename,
                    "client_count": len(clients),
                    "document_count": len(documents),
                    "month": month,
                }

                # Inspect every uploaded filename across all months.
                # Monthly filtering will be applied to the client comparison.
                file_results = inspect_documents(documents, clients)

                # Apply the selected month to the client comparison.
                # The filename audit still contains files from every month.
                client_report = build_client_report(
                    clients, file_results, month
                )

                # Export the same results and month displayed in the table.
                missing_report_download = build_missing_report_download(
                    client_report, month
                )

                # Create drafts only for clients with missing requirements.
                reminders = build_reminders(client_report, month)

            except ValueError as validation_error:
                # Report invalid client-register data through the template.
                error = str(validation_error)

    # Pass both the client comparison and the complete file audit to HTML.
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


# Display a readable error when the complete request exceeds 25 MB.
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


# Start the local development server when this file is run directly.
# On Render, Gunicorn imports the app instead, so this block is skipped.
if __name__ == "__main__":
    app.run()