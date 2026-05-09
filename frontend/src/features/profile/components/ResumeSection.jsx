import { useMemo, useState } from 'react';
import { FileText, Trash2, Upload, Wand2 } from 'lucide-react';
import api from '../../../lib/api.js';
import { Alert, AlertDescription } from '../../../components/ui/alert.jsx';
import { Button } from '../../../components/ui/button.jsx';
import { Spinner } from '../../../components/ui/spinner.jsx';

const ResumeSection = ({ profile, activeResume, onChanged }) => {
	const [selectedFile, setSelectedFile] = useState(null);
	const [isUploading, setIsUploading] = useState(false);
	const [isDeleting, setIsDeleting] = useState(false);
	const [error, setError] = useState('');
	const [showBuilder, setShowBuilder] = useState(false);

	const builderSections = useMemo(() => {
		const name = [profile?.prenom, profile?.nom].filter(Boolean).join(' ');
		return [
			{ label: 'Identity', value: name || 'Add your name in Basic Information.' },
			{ label: 'Target roles', value: (profile?.target_roles || []).join(', ') || 'Add target roles.' },
			{ label: 'Skills', value: (profile?.competences || []).join(', ') || 'Add skills.' },
			{ label: 'Interests', value: (profile?.domaines_interet || []).join(', ') || 'Add industries.' },
		];
	}, [profile]);

	const uploadResume = async () => {
		if (!selectedFile) {
			setError('Choose a PDF or DOCX resume first.');
			return;
		}

		setError('');
		setIsUploading(true);
		const formData = new FormData();
		formData.append('file', selectedFile);
		try {
			await api.post('/profile/resume/', formData, {
				headers: { 'Content-Type': 'multipart/form-data' },
			});
			setSelectedFile(null);
			await onChanged?.();
		} catch (err) {
			setError(err.response?.data?.file?.[0] || err.response?.data?.detail || 'Resume upload failed.');
		} finally {
			setIsUploading(false);
		}
	};

	const deleteResume = async () => {
		setError('');
		setIsDeleting(true);
		try {
			await api.delete('/profile/resume/');
			await onChanged?.();
		} catch (err) {
			setError(err.response?.data?.detail || 'Could not remove the resume.');
		} finally {
			setIsDeleting(false);
		}
	};

	return (
		<div className="space-y-4">
			{error ? (
				<Alert variant="destructive">
					<AlertDescription>{error}</AlertDescription>
				</Alert>
			) : null}

			<div className="grid gap-3 sm:grid-cols-2">
				<div className="rounded-md border border-neutral-200 bg-white p-4">
					<div className="flex items-start gap-3">
						<Upload className="mt-0.5 h-5 w-5 text-neutral-500" aria-hidden="true" />
						<div className="min-w-0 flex-1 space-y-3">
							<div>
								<p className="font-medium text-neutral-900">Upload Resume</p>
								<p className="text-sm text-neutral-500">PDF or DOCX, up to 5 MB.</p>
							</div>
							<input
								type="file"
								accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
								onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
								className="block w-full text-sm text-neutral-600 file:mr-3 file:rounded-md file:border-0 file:bg-neutral-100 file:px-3 file:py-2 file:text-sm file:font-medium file:text-neutral-700"
							/>
							<Button type="button" onClick={uploadResume} disabled={isUploading}>
								{isUploading ? <Spinner size={16} className="mr-2" /> : null}
								Upload Resume
							</Button>
						</div>
					</div>
				</div>

				<div className="rounded-md border border-neutral-200 bg-white p-4">
					<div className="flex items-start gap-3">
						<Wand2 className="mt-0.5 h-5 w-5 text-neutral-500" aria-hidden="true" />
						<div className="min-w-0 flex-1 space-y-3">
							<div>
								<p className="font-medium text-neutral-900">Build a BidWise Resume</p>
								<p className="text-sm text-neutral-500">A structured resume draft from your profile signals.</p>
							</div>
							<Button type="button" variant="outline" onClick={() => setShowBuilder((value) => !value)}>
								{showBuilder ? 'Hide builder' : 'Open builder'}
							</Button>
						</div>
					</div>
				</div>
			</div>

			{activeResume ? (
				<div className="flex flex-col gap-3 rounded-md border border-green-200 bg-green-50 p-4 sm:flex-row sm:items-center sm:justify-between">
					<div className="flex items-center gap-3">
						<FileText className="h-5 w-5 text-green-700" aria-hidden="true" />
						<div>
							<p className="font-medium text-green-950">Active resume attached</p>
							<p className="text-sm text-green-800">{activeResume.metadata?.original_filename || 'Uploaded resume'}</p>
						</div>
					</div>
					<Button type="button" variant="outline" onClick={deleteResume} disabled={isDeleting}>
						{isDeleting ? <Spinner size={16} className="mr-2" /> : <Trash2 className="mr-2 h-4 w-4" />}
						Remove
					</Button>
				</div>
			) : null}

			{showBuilder ? (
				<div className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
					<div className="grid gap-3 sm:grid-cols-2">
						{builderSections.map((section) => (
							<div key={section.label}>
								<p className="text-xs font-semibold uppercase text-neutral-500">{section.label}</p>
								<p className="mt-1 text-sm text-neutral-800">{section.value}</p>
							</div>
						))}
					</div>
				</div>
			) : null}
		</div>
	);
};

export default ResumeSection;
