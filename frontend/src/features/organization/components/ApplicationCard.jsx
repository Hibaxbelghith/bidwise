import { useState } from 'react';
import { Download, FileText, X } from 'lucide-react';
import { getApplicationStatusMeta } from '../../applications/applicationStatusUi.js';
import { rejectApplication } from '../services/organizationService.js';

const formatDate = (dateString) => {
  if (!dateString) return '';
  try {
    const date = new Date(dateString);
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return `Applied ${date.toLocaleDateString('en-GB', options)}`;
  } catch {
    return '';
  }
};

const ApplicationCard = ({ application, opportunityId, onReject, showOpportunity = false }) => {
  const statusConfig = getApplicationStatusMeta(application.statut, 'organization');
  const showRejectButton =
    application.statut === 'SUBMITTED'
    || application.statut === 'VIEWED_BY_ORGANIZATION'
    || application.statut === 'SHORTLISTED';
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);

  const handleConfirmReject = async () => {
    setIsRejecting(true);
    try {
      await rejectApplication(opportunityId, application.id);
      setShowConfirmation(false);
      onReject(application.id);
    } catch (error) {
      console.error('Error rejecting application:', error);
      // Optionally show error to user here
    } finally {
      setIsRejecting(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {/* Name and Status */}
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-semibold text-neutral-900">{application.candidate_name}</h3>
            <span className={`inline-block px-2.5 py-0.5 text-xs font-medium rounded border ${statusConfig.bgColor} ${statusConfig.textColor} ${statusConfig.borderColor}`}>
              {statusConfig.label}
            </span>
          </div>

          {/* Email and Phone */}
          <p className="text-sm text-neutral-600 mb-2">
            {application.candidate_email}
            {application.contact_phone && ` · ${application.contact_phone}`}
          </p>

          {/* Opportunity Link (if showOpportunity) */}
          {showOpportunity && application.opportunity_title && (
            <p className="text-sm text-neutral-600 mb-2">
              Applied to: <a href={`/organization/opportunities/${application.opportunity_id}/applications`} className="text-blue-600 hover:text-blue-700 font-medium">{application.opportunity_title}</a>
            </p>
          )}

          {/* Applied Date */}
          <p className="text-xs text-neutral-500 mb-3">
            {formatDate(application.submitted_at)}
          </p>

          {/* Links to CV and Cover Letter */}
          <div className="flex items-center gap-3 text-sm">
            {application.cv_url && (
              <a
                href={application.cv_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-blue-600 hover:text-blue-700 font-medium"
              >
                <Download className="h-4 w-4" />
                Download CV
              </a>
            )}
            {application.cover_letter_url && (
              <a
                href={application.cover_letter_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-blue-600 hover:text-blue-700 font-medium"
              >
                <FileText className="h-4 w-4" />
                Cover letter
              </a>
            )}
          </div>
        </div>

        {/* Reject Button or Confirmation */}
        {showRejectButton && (
          <>
            {!showConfirmation ? (
              <button
                onClick={() => setShowConfirmation(true)}
                className="ml-4 flex items-center gap-2 px-3 py-2 text-sm font-medium text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
                title="Reject this application"
              >
                <X className="h-4 w-4" />
                Reject
              </button>
            ) : (
              <div className="ml-4 rounded-lg border border-red-200 bg-red-50 p-3 min-w-max">
                <p className="text-sm font-medium text-red-900 mb-2">Reject this application?</p>
                <p className="text-xs text-red-800 mb-3">
                  {application.candidate_name} will no longer be considered for this position.
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowConfirmation(false)}
                    disabled={isRejecting}
                    className="px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 rounded border border-red-300 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirmReject}
                    disabled={isRejecting}
                    className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded disabled:opacity-50"
                  >
                    {isRejecting ? 'Rejecting...' : 'Reject application'}
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ApplicationCard;
