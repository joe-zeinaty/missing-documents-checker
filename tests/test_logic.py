import base64
import csv
import io
import unittest
from types import SimpleNamespace

from client_parser import parse_clients
from document_checker import inspect_documents, build_client_report
from filename_parser import parse_filename
from reminder_builder import build_reminders
from report_export import build_missing_report_download


class DocumentLogicTests(unittest.TestCase):
    """Check the main rules without running the web server."""

    def setUp(self):
        # Create a fresh fictional register before every test.
        # K1040 requires two categories; K1043 requires only bank.
        self.csv_text = (
            "client_id,name,email,required_documents\n"
            "K1040,Alex Morgan,alex@example.com,bank;payroll\n"
            "K1043,Jamie Chen,jamie@example.com,bank\n"
        )

        self.clients = self.parse_csv(self.csv_text)

    @staticmethod
    def parse_csv(text):
        # Simulate an uploaded CSV using an in-memory byte stream.
        return parse_clients(io.BytesIO(text.encode("utf-8-sig")))

    @staticmethod
    def uploads(*filenames):
        # The checker reads filenames only, so PDF contents are unnecessary.
        return [
            SimpleNamespace(filename=filename)
            for filename in filenames
        ]

    def test_client_id_validation(self):
        # Lowercase IDs should normalize to uppercase.
        clients = self.parse_csv(
            self.csv_text.replace("K1040", "k1040")
        )
        self.assertEqual(clients[0]["client_id"], "K1040")

        # IDs with fewer than four digits must be rejected.
        with self.assertRaises(ValueError):
            self.parse_csv(self.csv_text.replace("K1040", "K104"))

    def test_invalid_register_data(self):
        # Check three independent register errors.
        invalid_registers = [
            self.csv_text.replace("required_documents", "documents"),
            self.csv_text.replace("bank;payroll", "bank;invalid"),
            self.csv_text + "k1040,Duplicate,d@example.com,bank\n",
        ]

        for content in invalid_registers:
            with self.subTest(content=content):
                with self.assertRaises(ValueError):
                    self.parse_csv(content)

    def test_filename_variations(self):
        # All these names should identify the same document requirement.
        filenames = [
            "K1040_invoices_in_2026-08.pdf",
            "k1040-InvoicesIn-Aug2026.PDF",
            "K1040_invoices_in_August_2026.pdf",
            "K1040_invoices_in_08-2026 (1).pdf",
        ]

        for filename in filenames:
            with self.subTest(filename=filename):
                result = parse_filename(filename)
                self.assertEqual(
                    result["normalized_filename"],
                    "K1040_invoices_in_2026-08.pdf",
                )

    def test_invalid_filenames(self):
        # Reject unsupported extensions, malformed IDs and invalid dates.
        filenames = [
            "K1040_bank_2026-08.xlsx",
            "K1040_bank_2026-08.pdf.tmp",
            "Thumbs.db",
            "K104_bank_2026-08.pdf",
            "K1040_bank_2026-13.pdf",
            "K1040_unknown_2026-08.pdf",
        ]

        for filename in filenames:
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    parse_filename(filename)

    def test_repeated_submissions(self):
        # Naming variations for the same client/type/month count once.
        files = self.uploads(
            "K1040_bank_2026-08.pdf",
            "K1040_bank_2026-08 (1).pdf",
            "k1040-bank-Aug2026.pdf",
        )

        results = inspect_documents(files, self.clients)

        self.assertEqual(
            [result["status"] for result in results],
            ["Recognized", "Repeated submission", "Repeated submission"],
        )

        report = build_client_report(self.clients, results, "2026-08")

        # Bank is delivered, but payroll is still missing.
        self.assertEqual(report[0]["documents"]["bank"], "Delivered")
        self.assertEqual(report[0]["missing_documents"], ["payroll"])

    def test_unknown_client(self):
        # A well-formed filename cannot satisfy an unregistered client.
        results = inspect_documents(
            self.uploads("K9999_bank_2026-08.pdf"),
            self.clients,
        )

        self.assertEqual(results[0]["status"], "Unknown client")

    def test_month_filtering(self):
        # July remains valid but must not satisfy an August requirement.
        results = inspect_documents(
            self.uploads("K1040_bank_2026-07.pdf"),
            self.clients,
        )

        self.assertEqual(results[0]["status"], "Recognized")

        july = build_client_report(self.clients, results, "2026-07")
        august = build_client_report(self.clients, results, "2026-08")

        self.assertEqual(july[0]["documents"]["bank"], "Delivered")
        self.assertEqual(august[0]["documents"]["bank"], "Missing")

    def test_no_documents_uploaded(self):
        # Every CSV client must appear even when the upload batch is empty.
        report = build_client_report(self.clients, [], "2026-08")

        self.assertEqual(len(report), 2)
        self.assertEqual(report[0]["missing_count"], 2)
        self.assertEqual(report[1]["missing_count"], 1)
        self.assertEqual(
            report[1]["documents"]["payroll"],
            "Not required",
        )

    def test_csv_export_and_reminders(self):
        # Supply both bank documents; only Alex's payroll remains missing.
        results = inspect_documents(
            self.uploads(
                "K1040_bank_2026-08.pdf",
                "K1043_bank_2026-08.pdf",
            ),
            self.clients,
        )
        report = build_client_report(self.clients, results, "2026-08")

        # Decode the download into CSV rows and verify its exact contents.
        encoded_csv = build_missing_report_download(report, "2026-08")
        csv_text = base64.b64decode(encoded_csv).decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(csv_text))

        self.assertEqual(
            reader.fieldnames,
            ["client_id", "name", "email", "document", "month"],
        )
        self.assertEqual(
            list(reader),
            [{
                "client_id": "K1040",
                "name": "Alex Morgan",
                "email": "alex@example.com",
                "document": "payroll",
                "month": "2026-08",
            }],
        )

        # Only the incomplete client should receive a draft.
        reminders = build_reminders(report, "2026-08")

        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0]["email"], "alex@example.com")
        self.assertIn("August 2026", reminders[0]["subject"])
        self.assertIn("- Payroll records", reminders[0]["body"])
        self.assertNotIn("- Bank statements", reminders[0]["body"])

    def test_complete_batch(self):
        # Supply every requirement for both clients.
        results = inspect_documents(
            self.uploads(
                "K1040_bank_2026-08.pdf",
                "K1040_payroll_2026-08.pdf",
                "K1043_bank_2026-08.pdf",
            ),
            self.clients,
        )
        report = build_client_report(self.clients, results, "2026-08")

        self.assertTrue(
            all(client["missing_count"] == 0 for client in report)
        )
        self.assertEqual(build_reminders(report, "2026-08"), [])

        # A complete batch should still produce a CSV containing headers.
        encoded_csv = build_missing_report_download(report, "2026-08")
        csv_text = base64.b64decode(encoded_csv).decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(csv_text)))

        self.assertEqual(len(rows), 1)


# Allow this test module to run directly as well as through discovery.
if __name__ == "__main__":
    unittest.main()