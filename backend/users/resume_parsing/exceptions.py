class ResumeParsingError(Exception):
    code = "parsing_failed"

    def __init__(self, message="Resume parsing failed."):
        super().__init__(message)


class ResumeParserDependencyMissing(ResumeParsingError):
    code = "dependency_missing"


class UnsupportedResumeFormat(ResumeParsingError):
    code = "unsupported_format"


class EncryptedResumeError(ResumeParsingError):
    code = "encrypted_pdf"


class EmptyResumeTextError(ResumeParsingError):
    code = "empty_text"
