import { ExternalLink, FileText, Loader2, Trash2, Upload } from 'lucide-react';
import { useState } from 'react';

import { Button } from '../../../components/ui/button.jsx';
import { Input } from '../../../components/ui/input.jsx';
import {
  ALLOWED_TENDER_DOCUMENT_ACCEPT,
  TENDER_DOCUMENT_TYPES,
} from '../opportunityPostConstants.js';
import { validateTenderDocumentFile } from '../opportunityPostValidation.js';
import { uploadOrganizationTenderDocument } from '../services/organizationService.js';
import { FieldError } from './OpportunityPostFields.jsx';

const formatFileSize = (bytes) => {
  const size = Number(bytes || 0);
  if (!size) return '';
  if (size < 1024 * 1024) return `${Math.round(size / 1024)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

const TenderDocumentsEditor = ({ documents, error, onChange, onUploadingChange }) => {
  const [uploadingType, setUploadingType] = useState('');
  const [fileErrors, setFileErrors] = useState({});

  const updateDocument = (index, patch) => {
    onChange(documents.map((document, documentIndex) => (
      documentIndex === index ? { ...document, ...patch } : document
    )));
  };

  const clearFileError = (type) => {
    setFileErrors((current) => {
      if (!current[type]) return current;
      const next = { ...current };
      delete next[type];
      return next;
    });
  };

  const handleFileChange = async (index, file) => {
    const document = documents[index];
    if (!document || !file) return;

    const validationError = validateTenderDocumentFile(file);
    if (validationError) {
      setFileErrors((current) => ({ ...current, [document.type]: validationError }));
      return;
    }

    clearFileError(document.type);
    setUploadingType(document.type);
    onUploadingChange?.(true);
    try {
      const uploaded = await uploadOrganizationTenderDocument({
        file,
        type: document.type,
        label: document.label,
      });
      updateDocument(index, {
        url: uploaded.url || '',
        label: uploaded.label || document.label,
        filename: uploaded.filename || file.name,
        size: uploaded.size || file.size,
      });
    } catch (uploadError) {
      const data = uploadError?.response?.data;
      setFileErrors((current) => ({
        ...current,
        [document.type]: data?.file?.[0] || data?.detail || 'Document upload failed.',
      }));
    } finally {
      setUploadingType('');
      onUploadingChange?.(false);
    }
  };

  const removeDocument = (index) => {
    clearFileError(documents[index]?.type);
    updateDocument(index, { url: '', filename: '', size: '' });
  };

  return (
    <div>
      <h2 className="text-sm font-semibold text-neutral-900">Documents</h2>
      <p className="mt-1 text-sm text-neutral-500">Upload PDF, DOCX, or DOC files. Max 5 MB per document.</p>
      <FieldError message={error} />

      <div className="mt-4 space-y-4">
        {documents.map((document, index) => {
          const option = TENDER_DOCUMENT_TYPES.find((item) => item.value === document.type);
          const label = option?.label || 'Document';
          const isUploading = uploadingType === document.type;
          const fileName = document.filename || document.label || label;
          const fileError = fileErrors[document.type];

          return (
            <div key={document.type} className="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-neutral-700">{label}</p>
                  {document.url ? (
                    <div className="mt-2 flex min-w-0 items-center gap-2 text-sm text-neutral-800">
                      <FileText className="h-4 w-4 shrink-0 text-blue-700" aria-hidden="true" />
                      <span className="truncate font-medium">{fileName}</span>
                      {document.size ? <span className="shrink-0 text-xs text-neutral-500">{formatFileSize(document.size)}</span> : null}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-neutral-500">No file uploaded yet.</p>
                  )}
                </div>

                <div className="flex flex-wrap gap-2">
                  {document.url ? (
                    <>
                      <Button type="button" variant="outline" size="sm" asChild>
                        <a href={document.url} target="_blank" rel="noreferrer">
                          <ExternalLink className="h-4 w-4" aria-hidden="true" />
                          Open
                        </a>
                      </Button>
                      <Button type="button" variant="outline" size="sm" onClick={() => removeDocument(index)}>
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                        Remove
                      </Button>
                    </>
                  ) : null}
                </div>
              </div>

              <div className="mt-4">
                <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm font-semibold text-neutral-800 hover:bg-neutral-100">
                  {isUploading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Upload className="h-4 w-4" aria-hidden="true" />}
                  {document.url ? 'Replace file' : 'Upload file'}
                  <Input
                    type="file"
                    accept={ALLOWED_TENDER_DOCUMENT_ACCEPT}
                    className="sr-only"
                    disabled={isUploading}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      event.target.value = '';
                      handleFileChange(index, file);
                    }}
                  />
                </label>
                <FieldError message={fileError} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default TenderDocumentsEditor;
