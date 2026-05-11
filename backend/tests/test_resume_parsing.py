import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import ProfileResume, Utilisateur
from users.resume_parsing import MAX_PARSED_TEXT_CHARS, clean_resume_text, parse_resume_file
from users.resume_parsing.exceptions import EmptyResumeTextError, ResumeParsingError
from users.tasks import parse_profile_resume


TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="bidwise_resume_parsing_")


def tearDownModule():
    shutil.rmtree(TEST_MEDIA_ROOT, ignore_errors=True)


def make_pdf_bytes(text):
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
    ]

    payload = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"

    xref_offset = len(payload)
    payload += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    payload += b"0000000000 65535 f \n"
    for offset in offsets:
        payload += f"{offset:010d} 00000 n \n".encode("ascii")
    payload += (
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
        + b"startxref\n"
        + f"{xref_offset}\n".encode("ascii")
        + b"%%EOF\n"
    )
    return payload


def make_docx_bytes(*paragraphs):
    from docx import Document

    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, PROFILE_RESUME_USE_CLOUDINARY=False)
class ResumeParsingServiceTests(TestCase):
    def test_clean_resume_text_preserves_multilingual_unicode(self):
        text = clean_resume_text("\x00  Développeur   backend\nمهندس تعلم الآلة   Python  ")

        self.assertEqual(text, "Développeur backend مهندس تعلم الآلة Python")
        self.assertIn("Développeur", text)
        self.assertIn("مهندس تعلم الآلة", text)
        self.assertNotIn("\x00", text)

    def test_clean_resume_text_truncates_safely(self):
        text = clean_resume_text("Python " * 100, max_length=25)

        self.assertLessEqual(len(text), 25)
        self.assertTrue(text.startswith("Python"))

    def test_pdf_extraction(self):
        upload = SimpleUploadedFile(
            "resume.pdf",
            make_pdf_bytes("Backend Django APIs PostgreSQL"),
            content_type="application/pdf",
        )

        parsed = parse_resume_file(upload)

        self.assertEqual(parsed.parser, "pypdf")
        self.assertIn("Backend Django APIs PostgreSQL", parsed.text)

    def test_docx_extraction_preserves_arabic_and_french_accents(self):
        upload = SimpleUploadedFile(
            "resume.docx",
            make_docx_bytes("Développeur backend", "مهندس تعلم الآلة Python Django"),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        parsed = parse_resume_file(upload)

        self.assertEqual(parsed.parser, "python-docx")
        self.assertIn("Développeur backend", parsed.text)
        self.assertIn("مهندس تعلم الآلة", parsed.text)

    def test_corrupted_pdf_raises_safe_error(self):
        upload = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.4 corrupted",
            content_type="application/pdf",
        )

        with self.assertRaises(ResumeParsingError):
            parse_resume_file(upload)

    def test_empty_docx_raises_empty_text_error(self):
        upload = SimpleUploadedFile(
            "empty.docx",
            make_docx_bytes(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with self.assertRaises(EmptyResumeTextError):
            parse_resume_file(upload)


@override_settings(
    MEDIA_ROOT=TEST_MEDIA_ROOT,
    CELERY_TASK_ALWAYS_EAGER=True,
    PROFILE_RESUME_USE_CLOUDINARY=False,
)
class ResumeParsingTaskTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="resume_parser",
            email="resume_parser@example.com",
            password="x",
        )
        self.profile = self.user.profil

    def create_resume(self, name, content, content_type):
        return ProfileResume.objects.create(
            profile=self.profile,
            file=SimpleUploadedFile(name, content, content_type=content_type),
            source_type=ProfileResume.SourceType.UPLOAD,
            is_active=True,
        )

    def test_parse_task_persists_text_and_triggers_embedding_refresh(self):
        resume = self.create_resume(
            "resume.docx",
            make_docx_bytes("Backend Django APIs", "PostgreSQL Redis"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with patch("users.tasks.process_profile_resume_semantics", return_value={"status": "SUCCEEDED"}) as semantic:
            with patch("users.tasks.enqueue_profile_embedding_refresh", return_value=True) as mocked:
                result = parse_profile_resume.run(resume.pk)

        resume.refresh_from_db()
        self.assertEqual(result["status"], ProfileResume.ParsingStatus.SUCCEEDED)
        self.assertEqual(resume.parsing_status, ProfileResume.ParsingStatus.SUCCEEDED)
        self.assertIn("Backend Django APIs", resume.parsed_text)
        self.assertTrue(resume.parsed_at)
        self.assertEqual(resume.metadata["parser"], "python-docx")
        self.assertIn("PostgreSQL Redis", resume.resume_text_embedding_source)
        semantic.assert_called_once()
        mocked.assert_called_once_with(self.profile.pk)

    def test_parse_task_handles_corrupted_file_without_crashing(self):
        resume = self.create_resume(
            "broken.pdf",
            b"%PDF-1.4 broken",
            "application/pdf",
        )

        with patch("users.tasks.process_profile_resume_semantics") as semantic:
            with patch("users.tasks.enqueue_profile_embedding_refresh", return_value=True) as mocked:
                result = parse_profile_resume.run(resume.pk)

        resume.refresh_from_db()
        self.assertEqual(result["status"], ProfileResume.ParsingStatus.FAILED)
        self.assertEqual(resume.parsing_status, ProfileResume.ParsingStatus.FAILED)
        self.assertEqual(resume.parsed_text, "")
        self.assertTrue(resume.parsing_error)
        semantic.assert_not_called()
        mocked.assert_called_once_with(self.profile.pk)

    def test_parse_task_handles_empty_extraction(self):
        resume = self.create_resume(
            "empty.docx",
            make_docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with patch("users.tasks.process_profile_resume_semantics") as semantic:
            with patch("users.tasks.enqueue_profile_embedding_refresh", return_value=True):
                result = parse_profile_resume.run(resume.pk)

        resume.refresh_from_db()
        self.assertEqual(result["status"], ProfileResume.ParsingStatus.EMPTY)
        self.assertEqual(resume.parsing_status, ProfileResume.ParsingStatus.EMPTY)
        self.assertEqual(resume.parsed_text, "")
        semantic.assert_not_called()

    def test_parse_task_truncates_persisted_text(self):
        resume = self.create_resume(
            "long.docx",
            make_docx_bytes("Python " * (MAX_PARSED_TEXT_CHARS // 3)),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with patch("users.tasks.process_profile_resume_semantics", return_value={"status": "SUCCEEDED"}):
            with patch("users.tasks.enqueue_profile_embedding_refresh", return_value=True):
                parse_profile_resume.run(resume.pk)

        resume.refresh_from_db()
        self.assertLessEqual(len(resume.parsed_text), MAX_PARSED_TEXT_CHARS)
        self.assertTrue(resume.metadata["parsed_text_truncated"])

    def test_parse_task_delay_executes_with_eager_celery(self):
        resume = self.create_resume(
            "resume.docx",
            make_docx_bytes("Python Django"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        with patch("users.tasks.process_profile_resume_semantics", return_value={"status": "SUCCEEDED"}):
            with patch("users.tasks.enqueue_profile_embedding_refresh", return_value=True):
                result = parse_profile_resume.delay(resume.pk).get()

        resume.refresh_from_db()
        self.assertEqual(result["status"], ProfileResume.ParsingStatus.SUCCEEDED)
        self.assertIn("Python Django", resume.parsed_text)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT, PROFILE_RESUME_USE_CLOUDINARY=False)
class ResumeUploadParsingFlowTests(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            username="resume_upload",
            email="resume_upload@example.com",
            password="x",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_resume_upload_enqueues_async_parse_and_returns_pending_status(self):
        upload = SimpleUploadedFile(
            "resume.pdf",
            make_pdf_bytes("Frontend React JavaScript"),
            content_type="application/pdf",
        )

        with patch("users.views.enqueue_profile_resume_parse", return_value=True) as mocked:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/profile/resume/",
                    {"file": upload},
                    format="multipart",
                )

        self.assertEqual(response.status_code, 201)
        resume = ProfileResume.objects.get(profile=self.user.profil)
        self.assertEqual(resume.parsing_status, ProfileResume.ParsingStatus.PENDING)
        self.assertFalse(response.data["resume"]["parsed_text_available"])
        self.assertEqual(response.data["resume"]["parsing_status"], ProfileResume.ParsingStatus.PENDING)
        mocked.assert_called_once_with(resume.pk)
