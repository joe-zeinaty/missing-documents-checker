# Missing Documents Checker

I built this small web app to help a tax advisor check which documents clients have supplied for a particular month. It uses Python and Flask, with a simple HTML, CSS and JavaScript interface.

- Upload a client CSV and select the document files.
- Choose a month and see what is delivered, missing or not required.
- Download the missing-document report.
- Copy a reminder email draft for each client with missing documents. Nothing is sent automatically.

## 1. Running locally and deployment

### Run locally

I developed the app in VS Code on Windows using Python 3.13.1.

```powershell
# Download the project and open its folder.
git clone https://github.com/joe-zeinaty/missing-documents-checker.git
cd missing-documents-checker

# Create a separate Python environment and install the dependencies.
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Start the local app.
.\.venv\Scripts\python.exe app.py
```

- Open http://127.0.0.1:5000 in a browser.
- Stop the server with **Ctrl+C**.
- These commands do not require activating the environment or changing PowerShell security settings.

### Deployment

I pushed the project to GitHub and connected it to a Render Web Service with these settings:

- **Branch:** `main`
- **Runtime:** Python 3
- **Root directory:** left empty
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
- **Environment variable:** `PYTHON_VERSION=3.13.1`

Render provides the public web address and automatically deploys updates pushed to the connected branch. Other people can use the app through their browser without installing anything.

## 2. Assumptions and decisions

### Client list

The CSV uses these columns, with one row per client:

```csv
client_id,name,email,required_documents
K1040,Alex Morgan,alex@example.com,bank;invoices_in;invoices_out;payroll
```

- Client IDs are **K followed by four digits**. Lowercase `k` is accepted and converted to uppercase.
- Required document codes are `bank`, `invoices_in`, `invoices_out` and `payroll`, separated by semicolons.
- These mean bank statements, purchase invoices, sales invoices and payroll records.
- Invalid rows, duplicate client IDs and unknown document codes produce an error rather than being silently skipped.

### Document names

- The expected format is `K1040_invoices_in_2026-08.pdf`.
- Only PDF documents are accepted to limit the testing scope. The client list is uploaded separately as a CSV.
- Common differences in capitalization and separators are accepted, including `InvoicesIn`, `INVOICES_OUT` and lowercase client IDs.
- Dates such as `Aug2026`, `August_2026` and `08-2026` are converted to `2026-08`.
- August 2026 is only the default filter. Other months are valid and remain visible in the filename review section at the bottom of the page.
- Files for unknown clients, unsupported formats such as `.xlsx` or `.pdf.tmp`, and names the app cannot interpret are flagged for review. The app does not guess.
- Multiple files for the same client, document type and month satisfy the requirement once. They remain listed for manual review.
- A suffix such as `(1)` does not prove a file is newer, so the app does not automatically prefer it.

### Limits

- The app checks names, not contents. A matching name can count as delivered even if the file is empty or contains incorrect information.
- One matching file satisfies a document category; it does not prove that every individual invoice was supplied.
- Normalized names are previews. Original files are not renamed or deleted.
- Upload limits are 1 MB for the client CSV and 25 MB for the overall request to keep the demonstration manageable. These would need reviewing against typical client batches before real-world use.
- Files must be reselected after submitting the form, including when checking another month.
- There are no accounts or saved history. This is a demonstration, not a finished system for confidential client records.

### Checks completed

- I ran 10 automated tests covering validation, awkward filenames, repeated submissions, unknown clients, month filtering, empty batches, exports and reminders.
- I manually checked the local and deployed app, including downloading reports and copying drafts.
- Comparing the supplied client list against the 64-file filename list confirmed **61 August requirements: 56 delivered and 5 missing**. The exported report matched exactly.

```powershell
# Run the automated tests from the project folder.
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 3. What I would do with one more day

- Add a downloadable sample CSV and short instructions beside the upload fields.
- Show a clear warning when files need review, even while the filename review is collapsed.
- Add tests for upload limits, unusual CSV formatting and the full upload-to-report flow.
- Reject empty files and make changing the month more convenient.
- Ask someone unfamiliar with the app to try it and improve anything they find confusing.
- Add text validation for German language, given the location of clients
- Make the upload elements drag-and-drop for easier use
- Add the suggested LLM for reminder email generation

## 4. Where I used AI and why

- I used ChatGPT/Codex to help plan the structure, draft substantial parts of the Python and frontend code, suggest tests, troubleshoot issues and prepare this README.
- I worked through the implementation step by step, ran the tests, checked the results and made decisions about the app's behavior.
- AI helped me build faster while understanding why each part was needed. I did not treat generated code as automatically correct.
- **There is no AI inside the running app.** Matching follows fixed Python rules, and reminder emails use a fixed template. No uploaded data is sent to an AI service by the app.

## 5. How much time I spent

- 1st day i spent 3 hours preparing the stack i will be using after digesting the task requirements and deciding a structure for the software
- 2nd day i spent around 4 hours piecing together the code i got from the AI platform and testing as I go with the files provided
- 3rd day i spent around 5 hours on fixing the front-end enough to be well structured and readable for demonstration purposes and then preparing the README file and pushing everything onto github and making sure Render.com automatically applies all new funtionalities to the public URL
