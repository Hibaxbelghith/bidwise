import { useRef, useState, useEffect } from 'react';
import {
	Download,
	Eye,
	FileText,
	MoreVertical,
	RefreshCw,
	Sparkles,
	Trash2,
	Upload,
	X,
} from 'lucide-react';


import api from '../../../lib/api.js';
import { Alert, AlertDescription } from '../../../components/ui/alert.jsx';
import { Button } from '../../../components/ui/button.jsx';
import { Spinner } from '../../../components/ui/spinner.jsx';
import {
	ALLOWED_RESUME_ACCEPT,
	validateResumeFile,
} from '../profileValidation.js';
import { normalizeSkillList, normalizeTextList } from '../profilePreferences.js';

const getResumeFileName = (resume) =>
	resume?.metadata?.original_filename || resume?.file?.name || 'Uploaded resume';

const getResumeUrl = (resume) => resume?.file_url || resume?.previewUrl || '';

const isPreviewableInline = (resume) => {
	const fileName = getResumeFileName(resume).toLowerCase();
	const contentType = resume?.metadata?.content_type || resume?.file?.type || '';
	return fileName.endsWith('.pdf') || fileName.endsWith('.txt') || contentType === 'application/pdf' || contentType === 'text/plain';
};

const normalizeStatus = (value) => String(value || '').trim().toUpperCase();

const isResumeAnalysisRunning = (resume) => {
	const semanticStatus = normalizeStatus(resume?.semantic_resume_status);
	const parsingStatus = normalizeStatus(resume?.parsing_status);
	return ['PENDING', 'PROCESSING'].includes(semanticStatus) || parsingStatus === 'PROCESSING';
};

const isResumeAnalysisFinished = (resume) => {
	const semanticStatus = normalizeStatus(resume?.semantic_resume_status);
	return ['SUCCEEDED', 'COMPLETED', 'EMPTY', 'SKIPPED', 'FAILED'].includes(semanticStatus);
};

const MAX_PROFILE_SKILLS = 30;

const sessionKey = (prefix, resumeId) => `${prefix}_${resumeId}`;

const normalizeSuggestionItems = (value) => {
	if (Array.isArray(value)) {
		return value.map((item) => String(item || '').trim()).filter(Boolean);
	}
	const text = String(value ?? '').trim();
	return text ? [text] : [];
};

const hasValue = (values, candidate) => {
	const key = String(candidate || '').trim().toLowerCase();
	return normalizeSuggestionItems(values).some((value) => value.toLowerCase() === key);
};

const getResumeCanonicalRole = (resume) => {
	const metadata = resume?.semantic_resume_metadata;
	if (!metadata || typeof metadata !== 'object') return '';
	return String(metadata.canonical_role || metadata?.llm_enrichment?.result?.canonical_role || '').trim();
};

const getPendingResumeSuggestionId = (resume) => {
	if (!resume?.id) return '';
	try {
		return sessionStorage.getItem(sessionKey('resumeSuggestionsPending', resume.id)) === '1'
			? String(resume.id)
			: '';
	} catch {
		return '';
	}
};

const shouldHideResumeSuggestions = (resume) => {
	if (!resume?.id) return true;
	try {
		return sessionStorage.getItem(sessionKey('resumeSuggestionsSkipped', resume.id)) === '1'
			|| sessionStorage.getItem(sessionKey('resumeSuggestionsApplied', resume.id)) === '1';
	} catch {
		return false;
	}
};

const ResumeAnalysisCard = () => (
	<div className="rounded-md border border-blue-100 bg-blue-50/60 p-4">
		<div className="flex items-start gap-3">
			<span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-white text-blue-700 shadow-sm">
				<FileText className="h-5 w-5 animate-pulse" aria-hidden="true" />
			</span>
			<div className="min-w-0 flex-1">
				<p className="font-medium text-neutral-950">Analyzing your resume...</p>
				<div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-blue-100">
					<div className="h-full w-1/2 animate-pulse rounded-full bg-blue-600" />
				</div>
				<p className="mt-2 text-sm text-neutral-600">Extracting skills and experience</p>
			</div>
		</div>
	</div>
);

const ResumeAnalysisDelayedCard = ({ resume }) => (
	<div className="rounded-md border border-amber-200 bg-amber-50/70 p-4">
		<div className="flex items-start gap-3">
			<span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-white text-amber-700 shadow-sm">
				<FileText className="h-5 w-5" aria-hidden="true" />
			</span>
			<div className="min-w-0 flex-1">
				<p className="font-medium text-neutral-950">Resume uploaded successfully.</p>
				<p className="mt-1 text-sm text-neutral-700">AI analysis is taking longer than expected.</p>
				<p className="mt-1 text-sm text-neutral-600">Your recommendations will improve once analysis completes.</p>
				{resume ? (
					<p className="mt-2 truncate text-xs text-neutral-500">{getResumeFileName(resume)}</p>
				) : null}
			</div>
		</div>
	</div>
);

const ResumeSuggestionsCard = ({
	resume,
	profile,
	selectedRole,
	selectedSkills,
	onToggleRole,
	onToggleSkill,
	onApply,
	onSkip,
	isApplying,
}) => {
	const currentRoles = normalizeTextList(profile?.target_roles);
	const currentSkills = normalizeSkillList(profile?.competences);
	const skillLimit = Math.max(0, MAX_PROFILE_SKILLS - currentSkills.length);
	const role = getResumeCanonicalRole(resume);
	const suggestedRole = role && !hasValue(currentRoles, role) ? role : '';
	const suggestedSkills = normalizeSkillList(resume?.extracted_skills)
		.filter((skill) => !hasValue(currentSkills, skill))
		.slice(0, skillLimit);
	const hasSelected = Boolean(selectedRole) || selectedSkills.length > 0;

	if (
		!['SUCCEEDED', 'COMPLETED'].includes(normalizeStatus(resume?.semantic_resume_status))
		|| !resume?.id
		|| shouldHideResumeSuggestions(resume)
		|| !getPendingResumeSuggestionId(resume)
		|| normalizeSuggestionItems(resume?.extracted_skills).length === 0
		|| (!suggestedRole && suggestedSkills.length === 0)
	) {
		return null;
	}

	return (
		<div className="rounded-md border border-blue-100 bg-white p-4 shadow-sm">
			<div className="flex items-start gap-3">
				<span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-700">
					<Sparkles className="h-5 w-5" aria-hidden="true" />
				</span>
				<div className="min-w-0 flex-1">
					<p className="font-medium text-neutral-950">Add to your profile?</p>
					<p className="mt-1 text-sm text-neutral-600">We found these from your resume — select what to keep</p>
				</div>
			</div>

			<div className="mt-4 space-y-4">
				{suggestedRole ? (
					<div>
						<p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Detected role</p>
						<div className="mt-2 flex flex-wrap gap-2">
							<label className={`inline-flex cursor-pointer items-center gap-2 rounded-md border px-2.5 py-1.5 text-sm transition ${
								selectedRole ? 'border-blue-200 bg-blue-50 text-blue-900' : 'border-neutral-200 bg-neutral-50 text-neutral-700 hover:bg-neutral-100'
							}`}>
								<input
									type="checkbox"
									className="h-3.5 w-3.5 rounded border-neutral-300 text-blue-600"
									checked={Boolean(selectedRole)}
									onChange={() => onToggleRole(suggestedRole)}
								/>
								<span>{suggestedRole}</span>
							</label>
						</div>
					</div>
				) : null}

				{suggestedSkills.length > 0 ? (
					<div>
						<p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Skills</p>
						<div className="mt-2 flex flex-wrap gap-2">
							{suggestedSkills.map((skill) => {
								const checked = selectedSkills.includes(skill);
								return (
									<button
										key={skill}
										type="button"
										onClick={() => onToggleSkill(skill)}
										className={`rounded-md border px-2.5 py-1.5 text-sm transition ${
											checked
												? 'border-blue-200 bg-blue-50 text-blue-900'
												: 'border-neutral-200 bg-neutral-50 text-neutral-700 hover:bg-neutral-100'
										}`}
										aria-pressed={checked}
									>
										{skill}
									</button>
								);
							})}
						</div>
						<p className="mt-2 text-xs text-neutral-500">
							{skillLimit} profile skill slots available.
						</p>
					</div>
				) : null}
			</div>

			<div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				<Button type="button" variant="outline" onClick={onSkip} disabled={isApplying}>
					Skip
				</Button>
				<Button
					type="button"
					onClick={onApply}
					disabled={isApplying || !hasSelected}
					className="bg-neutral-950 text-white hover:bg-neutral-800"
				>
					{isApplying ? <Spinner size={16} className="mr-2" /> : null}
					Add selected to profile
				</Button>
			</div>
		</div>
	);
};

// Skeleton moderne pour le chargement
const ResumeUploadSkeleton = () => {
	const [progress, setProgress] = useState(0);
	const [status, setStatus] = useState('uploading');

	useEffect(() => {
		// Simulation de progression
		const interval = setInterval(() => {
			setProgress((prev) => {
				if (prev >= 90) {
					clearInterval(interval);
					setStatus('processing');
					return 90;
				}
				return prev + 10;
			});
		}, 300);

		return () => clearInterval(interval);
	}, []);

	return (
		<div className="flex flex-col items-center justify-center py-12 text-center">
			{/* Animation de chargement */}
			<div className="relative mb-6">
				<div className="h-20 w-20 rounded-full border-4 border-neutral-100 bg-white flex items-center justify-center">
					<FileText className="h-8 w-8 text-neutral-400 animate-pulse" />
				</div>
				<div className="absolute -bottom-1 -right-1 rounded-full bg-white p-0.5">
					<Spinner size={20} className="text-blue-600" />
				</div>
			</div>

			<h3 className="text-lg font-semibold text-neutral-900">
				{status === 'uploading' ? 'Uploading resume' : 'Processing your file'}
			</h3>
			
			<p className="mt-1 text-sm text-neutral-500">
				{status === 'uploading' 
					? 'This may take a few seconds' 
					: 'Analyzing and extracting information...'}
			</p>

			{/* Barre de progression */}
			<div className="mt-6 w-64">
				<div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
					<div
						className="h-full rounded-full bg-blue-600 transition-all duration-300 ease-out"
						style={{ width: `${progress}%` }}
					/>
				</div>
				<p className="mt-2 text-xs text-neutral-400">{progress}%</p>
			</div>
		</div>
	);
};

const ResumePreviewFrame = ({ resume }) => {
	const previewUrl = getResumeUrl(resume);
	const fileName = getResumeFileName(resume);

	if (!previewUrl) {
		return (
			<div className="flex h-72 items-center justify-center rounded-md border border-neutral-200 bg-neutral-50 p-6 text-center">
				<div>
					<FileText className="mx-auto h-10 w-10 text-neutral-400" aria-hidden="true" />
					<p className="mt-3 text-sm font-medium text-neutral-900">{fileName}</p>
					<p className="mt-1 text-sm text-neutral-500">Preview will be available after upload.</p>
				</div>
			</div>
		);
	}

	if (!isPreviewableInline(resume)) {
		return (
			<div className="flex h-72 items-center justify-center rounded-md border border-neutral-200 bg-neutral-50 p-6 text-center">
				<div className="space-y-3">
					<FileText className="mx-auto h-10 w-10 text-neutral-400" aria-hidden="true" />
					<p className="mt-3 text-sm font-medium text-neutral-900">{fileName}</p>
					<p className="mt-1 text-sm text-neutral-500">This file type is ready to use. Download it to inspect the original document.</p>
					{previewUrl ? (
						<Button asChild type="button" variant="outline">
							<a href={previewUrl} target="_blank" rel="noreferrer">
								<Download className="h-4 w-4" />
								Open file
							</a>
						</Button>
					) : null}
				</div>
			</div>
		);
	}

	return (
		<iframe
			title={`Resume preview - ${fileName}`}
			src={previewUrl}
			referrerPolicy="no-referrer"
			className="h-80 w-full rounded-md border border-neutral-200 bg-white"
		/>
	);
};

const ModalShell = ({ title, children, onClose }) => (
	<div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/40 px-4 py-6">
		<div className="w-full max-w-2xl rounded-lg border border-neutral-200 bg-white shadow-2xl">
			<div className="flex items-center justify-between border-b border-neutral-200 px-5 py-4">
				<h3 className="text-base font-semibold text-neutral-950">{title}</h3>
				{onClose ? (
					<button
						type="button"
						onClick={onClose}
						className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-900"
						aria-label="Close modal"
					>
						<X className="h-4 w-4" aria-hidden="true" />
					</button>
				) : null}
			</div>
			<div className="p-5">{children}</div>
		</div>
	</div>
);

const ResumeSection = ({ profile, activeResume, onChanged }) => {
	const fileInputRef = useRef(null);
	const onChangedRef = useRef(onChanged);
	const [isUploading, setIsUploading] = useState(false);
	const [isDeleting, setIsDeleting] = useState(false);
	const [isConfirming, setIsConfirming] = useState(false);
	const [isApplyingSuggestions, setIsApplyingSuggestions] = useState(false);
	const [error, setError] = useState('');
	const [previewResume, setPreviewResume] = useState(null);
	const [pendingResume, setPendingResume] = useState(null);
	const [polledResume, setPolledResume] = useState(null);
	const [selectedRole, setSelectedRole] = useState('');
	const [selectedSkills, setSelectedSkills] = useState([]);
	const [hiddenSuggestionResumeIds, setHiddenSuggestionResumeIds] = useState({});
	const [analysisTimedOut, setAnalysisTimedOut] = useState(false);
	const [menuOpen, setMenuOpen] = useState(false);

	useEffect(() => {
		onChangedRef.current = onChanged;
	}, [onChanged]);

	useEffect(() => {
		setPolledResume(null);
		setAnalysisTimedOut(false);
	}, [activeResume?.id]);

	const displayedResume = polledResume || activeResume;
	const analysisRunning = isResumeAnalysisRunning(displayedResume) && !analysisTimedOut;

	useEffect(() => {
		if (!displayedResume?.id || shouldHideResumeSuggestions(displayedResume)) {
			setSelectedRole('');
			setSelectedSkills([]);
			return;
		}
		const currentRoles = normalizeTextList(profile?.target_roles);
		const currentSkills = normalizeSkillList(profile?.competences);
		const skillLimit = Math.max(0, MAX_PROFILE_SKILLS - currentSkills.length);
		const role = getResumeCanonicalRole(displayedResume);
		setSelectedRole(role && !hasValue(currentRoles, role) ? role : '');
		setSelectedSkills(
			normalizeSkillList(displayedResume?.extracted_skills)
				.filter((skill) => !hasValue(currentSkills, skill))
				.slice(0, skillLimit)
		);
	}, [displayedResume?.id, displayedResume?.semantic_resume_updated_at, profile?.competences, profile?.target_roles, hiddenSuggestionResumeIds]);

	useEffect(() => {
		if (!displayedResume?.id || !analysisRunning) {
			return undefined;
		}

		let cancelled = false;
		const startedAt = Date.now();
		let intervalId;

		const pollResume = async () => {
			if (Date.now() - startedAt >= 120000) {
				window.clearInterval(intervalId);
				setAnalysisTimedOut(true);
				return;
			}

			try {
				const response = await api.get('/profile/resume/');
				if (cancelled) {
					return;
				}
				const nextResume = response.data?.resume || null;
				if (!nextResume) {
					setPolledResume(null);
					return;
				}
				setPolledResume(nextResume);
				if (isResumeAnalysisFinished(nextResume)) {
					window.clearInterval(intervalId);
					setAnalysisTimedOut(false);
					await onChangedRef.current?.();
				}
			} catch (err) {
				if (!cancelled) {
					setError(err.response?.data?.detail || 'Could not refresh resume analysis status.');
				}
			}
		};

		intervalId = window.setInterval(pollResume, 3000);
		pollResume();

		return () => {
			cancelled = true;
			window.clearInterval(intervalId);
		};
	}, [analysisRunning, displayedResume?.id]);

	const openFilePicker = () => {
		setMenuOpen(false);
		fileInputRef.current?.click();
	};

	const uploadResume = async (file) => {
		const validationError = validateResumeFile(file);
		if (validationError) {
			setError(validationError);
			return;
		}

		setError('');
		setIsUploading(true);
		const previousPendingResume = pendingResume;
		setPendingResume(null);
		const formData = new FormData();
		formData.append('file', file);
		formData.append('activate', 'false');

		try {
			if (previousPendingResume?.id) {
				await api.delete(`/profile/resume/?resume_id=${encodeURIComponent(previousPendingResume.id)}`);
			}
			const response = await api.post('/profile/resume/', formData, {
				headers: { 'Content-Type': 'multipart/form-data' },
			});
			const uploadedResume = response.data?.resume || null;
			setPendingResume(uploadedResume);
			setPreviewResume(uploadedResume);
		} catch (err) {
			setError(err.response?.data?.file?.[0] || err.response?.data?.detail || 'Resume upload failed.');
		} finally {
			setIsUploading(false);
			if (fileInputRef.current) {
				fileInputRef.current.value = '';
			}
		}
	};

	const confirmPendingResume = async () => {
		if (!pendingResume?.id) {
			setPreviewResume(null);
			return;
		}

		setError('');
		setIsConfirming(true);
		try {
			await api.patch('/profile/resume/', { resume_id: pendingResume.id });
			try {
				sessionStorage.setItem(sessionKey('resumeSuggestionsPending', pendingResume.id), '1');
				sessionStorage.removeItem(sessionKey('resumeSuggestionsSkipped', pendingResume.id));
				sessionStorage.removeItem(sessionKey('resumeSuggestionsApplied', pendingResume.id));
			} catch {
				// Session storage is an enhancement only.
			}
			setPendingResume(null);
			setPreviewResume(null);
			await onChanged?.();
		} catch (err) {
			setError(err.response?.data?.detail || 'Could not activate the resume.');
		} finally {
			setIsConfirming(false);
		}
	};

	const cancelPendingResume = async () => {
		const resumeToCancel = pendingResume;
		setPendingResume(null);
		setPreviewResume(null);
		if (!resumeToCancel?.id) {
			return;
		}

		setError('');
		setIsDeleting(true);
		try {
			await api.delete(`/profile/resume/?resume_id=${encodeURIComponent(resumeToCancel.id)}`);
		} catch (err) {
			setError(err.response?.data?.detail || 'Could not cancel the resume upload.');
			await onChanged?.();
		} finally {
			setIsDeleting(false);
		}
	};

	const toggleSuggestedRole = (role) => {
		setSelectedRole((current) => current ? '' : role);
	};

	const toggleSuggestedSkill = (skill) => {
		setSelectedSkills((current) => (
			current.includes(skill)
				? current.filter((value) => value !== skill)
				: [...current, skill].slice(0, Math.max(0, MAX_PROFILE_SKILLS - normalizeSkillList(profile?.competences).length))
		));
	};

	const hideResumeSuggestions = (resumeId, reason) => {
		if (!resumeId) return;
		try {
			sessionStorage.setItem(sessionKey(reason, resumeId), '1');
			sessionStorage.removeItem(sessionKey('resumeSuggestionsPending', resumeId));
		} catch {
			// Ignore unavailable session storage.
		}
		setHiddenSuggestionResumeIds((prev) => ({ ...prev, [resumeId]: true }));
		setSelectedRole('');
		setSelectedSkills([]);
	};

	const applySelectedSuggestions = async () => {
		if (!displayedResume?.id) return;
		const currentSkills = normalizeSkillList(profile?.competences);
		const currentRoles = normalizeTextList(profile?.target_roles);
		const availableSkillSlots = Math.max(0, MAX_PROFILE_SKILLS - currentSkills.length);
		const skillsToAdd = selectedSkills
			.filter((skill) => !hasValue(currentSkills, skill))
			.slice(0, availableSkillSlots);
		const nextRoles = selectedRole && !hasValue(currentRoles, selectedRole)
			? [...currentRoles, selectedRole]
			: currentRoles;

		if (skillsToAdd.length === 0 && nextRoles.length === currentRoles.length) {
			hideResumeSuggestions(displayedResume.id, 'resumeSuggestionsApplied');
			return;
		}

		setError('');
		setIsApplyingSuggestions(true);
		try {
			await api.put('/profile/me/', {
				competences: [...currentSkills, ...skillsToAdd],
				target_roles: nextRoles,
			});
			hideResumeSuggestions(displayedResume.id, 'resumeSuggestionsApplied');
			await onChanged?.({ preserveDraft: false });
		} catch (err) {
			setError(err.response?.data?.detail || err.response?.data?.competences?.[0] || err.response?.data?.target_roles?.[0] || 'Could not apply resume suggestions.');
		} finally {
			setIsApplyingSuggestions(false);
		}
	};

	const deleteResume = async () => {
		setError('');
		setIsDeleting(true);
		setMenuOpen(false);
		try {
			await api.delete('/profile/resume/');
			setPreviewResume(null);
			await onChanged?.();
		} catch (err) {
			setError(err.response?.data?.detail || 'Could not remove the resume.');
		} finally {
			setIsDeleting(false);
		}
	};

	const handleFileChange = (event) => {
		const file = event.target.files?.[0];
		if (file) {
			uploadResume(file);
		}
	};

	const previewIsPending = Boolean(pendingResume?.id && previewResume?.id === pendingResume.id);
	const closePreview = () => {
		if (previewIsPending) {
			cancelPendingResume();
			return;
		}
		setPreviewResume(null);
	};

	return (
		<div className="space-y-4">
			<input
				ref={fileInputRef}
				type="file"
				accept={ALLOWED_RESUME_ACCEPT}
				onChange={handleFileChange}
				className="hidden"
			/>

			{/* Modal de chargement moderne */}
			{isUploading ? (
				<ModalShell title="Resume & experience" onClose={() => {}}>
					<ResumeUploadSkeleton />
				</ModalShell>
			) : null}

			{previewResume ? (
				<ModalShell title="Resume preview" onClose={closePreview}>
					<div className="space-y-4">
						<div className="flex items-center gap-3 rounded-md border border-neutral-200 bg-neutral-50 p-3">
							<FileText className="h-5 w-5 text-neutral-500" aria-hidden="true" />
							<p className="min-w-0 truncate text-sm font-medium text-neutral-900">{getResumeFileName(previewResume)}</p>
						</div>
						<ResumePreviewFrame resume={previewResume} />
						<div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
							{!previewIsPending ? (
								<>
									<Button type="button" variant="outline" onClick={deleteResume} disabled={isDeleting}>
										{isDeleting ? <Spinner size={16} className="mr-2" /> : <Trash2 className="mr-2 h-4 w-4" />}
										Remove resume
									</Button>
									<Button type="button" variant="outline" onClick={openFilePicker}>
										<RefreshCw className="mr-2 h-4 w-4" />
										Upload another resume
									</Button>
								</>
							) : null}
							<Button
								type="button"
								className="bg-neutral-950 text-white hover:bg-neutral-800"
								onClick={previewIsPending ? confirmPendingResume : () => setPreviewResume(null)}
								disabled={isDeleting || isConfirming}
							>
								{isConfirming ? <Spinner size={16} className="mr-2" /> : null}
								Looks good
							</Button>
						</div>
					</div>
				</ModalShell>
			) : null}

			{error ? (
				<Alert variant="destructive">
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			) : null}

			<div className="grid gap-3 sm:grid-cols-2">
				<div className={`rounded-md border border-neutral-200 bg-white p-4 transition-shadow hover:shadow-sm ${displayedResume ? '' : 'sm:col-span-2'}`}>
					<div className="flex items-start gap-3">
						<Upload className="mt-0.5 h-5 w-5 text-neutral-500" aria-hidden="true" />
						<div className="min-w-0 flex-1 space-y-3">
							<div>
								<p className="font-medium text-neutral-900">Upload Resume</p>
								<p className="text-sm text-neutral-500">Use a pdf, docx, doc, rtf or txt. Max 5 MB.</p>
							</div>
							<Button type="button" onClick={openFilePicker} disabled={isUploading} className="bg-neutral-950 text-white hover:bg-neutral-800">
								<Upload className="mr-2 h-4 w-4" aria-hidden="true" />
								Upload Resume
							</Button>
						</div>
					</div>
				</div>

				{analysisRunning ? (
					<ResumeAnalysisCard />
				) : analysisTimedOut && displayedResume ? (
					<ResumeAnalysisDelayedCard resume={displayedResume} />
				) : displayedResume ? (
					<div className="relative flex flex-col gap-3 rounded-md border border-neutral-200 bg-white p-4 transition-shadow hover:shadow-sm sm:flex-row sm:items-center sm:justify-between">
						<div className="flex min-w-0 items-center gap-3">
							<span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-neutral-100 text-neutral-700">
								<FileText className="h-5 w-5" aria-hidden="true" />
							</span>
							<div className="min-w-0">
								<p className="font-medium text-neutral-950">Active resume attached</p>
								<p className="truncate text-sm text-neutral-600">{getResumeFileName(displayedResume)}</p>
							</div>
						</div>
						<div className="flex items-center gap-2">
							<Button type="button" variant="outline" onClick={() => setPreviewResume(displayedResume)}>
								<Eye className="mr-2 h-4 w-4" />
								Preview
							</Button>
							<div className="relative">
								<Button
									type="button"
									variant="outline"
									size="icon"
									onClick={() => setMenuOpen((value) => !value)}
									aria-label="Resume actions"
								>
									<MoreVertical className="h-4 w-4" />
								</Button>
								{menuOpen ? (
									<div className="absolute right-0 top-full z-20 mt-2 w-48 overflow-hidden rounded-md border border-neutral-200 bg-white shadow-lg">
										<button type="button" className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50" onClick={() => { setPreviewResume(displayedResume); setMenuOpen(false); }}>
											<Eye className="h-4 w-4" /> Preview
										</button>
										{getResumeUrl(displayedResume) ? (
											<a
												className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50"
												href={getResumeUrl(displayedResume)}
												target="_blank"
												rel="noreferrer"
											>
												<Download className="h-4 w-4" /> Download
											</a>
										) : null}
										<button type="button" className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-neutral-50" onClick={openFilePicker}>
											<RefreshCw className="h-4 w-4" /> Replace file
										</button>
										<button
											type="button"
											className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-700 hover:bg-red-50"
											onClick={deleteResume}
											disabled={isDeleting}
										>
											<Trash2 className="h-4 w-4" /> Delete
										</button>
									</div>
								) : null}
							</div>
						</div>
					</div>
				) : null}
			</div>

			<ResumeSuggestionsCard
				resume={displayedResume}
				profile={profile}
				selectedRole={selectedRole}
				selectedSkills={selectedSkills}
				onToggleRole={toggleSuggestedRole}
				onToggleSkill={toggleSuggestedSkill}
				onApply={applySelectedSuggestions}
				onSkip={() => hideResumeSuggestions(displayedResume?.id, 'resumeSuggestionsSkipped')}
				isApplying={isApplyingSuggestions}
			/>

		</div>
	);
};

export default ResumeSection;
