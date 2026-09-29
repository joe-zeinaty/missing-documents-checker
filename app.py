from datetime import datetime

from flask import Flask, render_template, request


# Create the Flask application.
app = Flask(__name__)

# Limit each complete upload request (CSV + documents) to 25 MB.
# Flask returns an HTTP 413 error if this limit is exceeded.
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# GET displays the form.
# POST handles the files and month submitted through the form.
@app.route("/", methods=["GET", "POST"])
def home():
    # Initial values used when someone first opens the page.
    month = "2026-08"
    error = None
    upload_summary = None

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
        if error is None:
            upload_summary = {
                "clients_filename": clients_file.filename,
                "document_count": len(documents),
                "month": month,
            }

    # Pass these variables to the HTML template.
    # They control the selected month and any messages displayed.
    return render_template(
        "index.html",
        month=month,
        error=error,
        upload_summary=upload_summary,
    )


# Display a readable message when an upload exceeds the request limit.
@app.errorhandler(413)
def upload_too_large(error):
    return render_template(
        "index.html",
        month="2026-08",
        error="The total upload exceeds 25 MB. Please select fewer files.",
        upload_summary=None,
    ), 413


# Start the local development server when this file is run directly.
# On Render, Gunicorn imports the app instead, so this block is skipped.
if __name__ == "__main__":
    app.run()