import { useRef, useState, useEffect } from 'react';
import {
	Download,
	Eye,
	FileText,
	MoreVertical,
	RefreshCw,
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

const getResumeFileName = (resume) =>
	resume?.metadata?.original_filename || resume?.file?.name || 'Uploaded resume';

const getResumeUrl = (resume) => resume?.file_url || resume?.previewUrl || '';

const isPreviewableInline = (resume) => {
	const fileName = getResumeFileName(resume).toLowerCase();
	const contentType = resume?.metadata?.content_type || resume?.file?.type || '';
	return fileName.endsWith('.pdf') || fileName.endsWith('.txt') || contentType === 'application/pdf' || contentType === 'text/plain';
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

const ResumeSection = ({ activeResume, onChanged }) => {
	const fileInputRef = useRef(null);
	const [isUploading, setIsUploading] = useState(false);
	const [isDeleting, setIsDeleting] = useState(false);
	const [isConfirming, setIsConfirming] = useState(false);
	const [error, setError] = useState('');
	const [previewResume, setPreviewResume] = useState(null);
	const [pendingResume, setPendingResume] = useState(null);
	const [menuOpen, setMenuOpen] = useState(false);

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

	const displayedResume = activeResume;
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

				{displayedResume ? (
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

		</div>
	);
};

export default ResumeSection;
