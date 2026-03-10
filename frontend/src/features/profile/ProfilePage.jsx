import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '../../components/ui/button.jsx';
import { Input } from '../../components/ui/input.jsx';
import { Label } from '../../components/ui/label.jsx';
import { Textarea } from '../../components/ui/textarea.jsx';
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from '../../components/ui/select.jsx';
import { Badge } from '../../components/ui/badge.jsx';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '../../components/ui/card.jsx';
import { Alert, AlertDescription } from '../../components/ui/alert.jsx';
import { ArrowLeft, CheckCircle2, Plus, X } from 'lucide-react';
import { Spinner } from '../../components/ui/spinner.jsx';
import { useAuth } from '../auth/AuthContext.jsx';

const EXPERIENCE_OPTIONS = [
	{ value: 'DEBUTANT', label: 'Débutant (0–1 an)' },
	{ value: 'JUNIOR', label: 'Junior (1–3 ans)' },
	{ value: 'CONFIRME', label: 'Confirmé (3–5 ans)' },
	{ value: 'SENIOR', label: 'Senior (5+ ans)' },
];

const splitList = (value) =>
	value
		? value
				.split(',')
				.map((item) => item.trim())
				.filter(Boolean)
		: [];

const joinList = (items) => items.map((item) => item.trim()).filter(Boolean).join(', ');

const Profile = () => {
	const { user, updateUserProfile } = useAuth();
	const [formData, setFormData] = useState({
		firstName: '',
		lastName: '',
		experienceLevel: '',
		yearsOfExperience: '',
		bio: '',
	});
	const [skills, setSkills] = useState([]);
	const [newSkill, setNewSkill] = useState('');
	const [interests, setInterests] = useState([]);
	const [newInterest, setNewInterest] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const [showSuccess, setShowSuccess] = useState(false);
	const [formError, setFormError] = useState('');

	useEffect(() => {
		if (!user) return;
		setFormData({
			firstName: user?.profil?.prenom || user?.first_name || '',
			lastName: user?.profil?.nom || user?.last_name || '',
			experienceLevel: user?.profil?.niveau_experience || '',
			yearsOfExperience: user?.profil?.annees_experience?.toString() || '',
			bio: user?.profil?.bio || '',
		});
		setSkills(splitList(user?.profil?.competences));
		setInterests(splitList(user?.profil?.domaines_interet));
	}, [user]);

	const handleChange = (field, value) => {
		setFormData((prev) => ({ ...prev, [field]: value }));
	};

	const addSkill = () => {
		const trimmed = newSkill.trim();
		if (trimmed && !skills.includes(trimmed)) {
			setSkills([...skills, trimmed]);
			setNewSkill('');
		}
	};

	const removeSkill = (skill) => {
		setSkills(skills.filter((item) => item !== skill));
	};

	const addInterest = () => {
		const trimmed = newInterest.trim();
		if (trimmed && !interests.includes(trimmed)) {
			setInterests([...interests, trimmed]);
			setNewInterest('');
		}
	};

	const removeInterest = (interest) => {
		setInterests(interests.filter((item) => item !== interest));
	};

	const handleSubmit = async (event) => {
		event.preventDefault();
		setFormError('');
		setShowSuccess(false);

		setIsLoading(true);
		const payload = {
			prenom: formData.firstName,
			nom: formData.lastName,
			competences: joinList(skills),
			domaines_interet: joinList(interests),
			niveau_experience: formData.experienceLevel || null,
			annees_experience: formData.yearsOfExperience
				? Number(formData.yearsOfExperience)
				: null,
		};

		const result = await updateUserProfile(payload);
		setIsLoading(false);

		if (result.success) {
			setShowSuccess(true);
			setTimeout(() => setShowSuccess(false), 3000);
		} else if (result.error) {
			setFormError(result.error);
		}
	};

	return (
		<div className="min-h-screen bg-neutral-50">
			<div className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:px-8">
				<div className="mb-8">
					<Link
						to="/dashboard"
						className="mb-4 inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900"
					>
						<ArrowLeft className="h-4 w-4" />
						Back to dashboard
					</Link>
					<h1 className="mb-2 text-3xl font-bold text-neutral-900">My Profile</h1>
					<p className="text-neutral-600">
						Keep your profile up to date to get better opportunity recommendations
					</p>
				</div>

				{showSuccess && (
					<Alert className="mb-6 border-green-200 bg-green-50">
						<CheckCircle2 className="h-4 w-4 text-green-600" />
						<AlertDescription className="text-green-800">
							Profile updated successfully!
						</AlertDescription>
					</Alert>
				)}

				{formError && (
					<Alert variant="destructive" className="mb-6">
						<AlertDescription>{formError}</AlertDescription>
					</Alert>
				)}

				<form onSubmit={handleSubmit} className="space-y-6">
					<Card>
						<CardHeader>
							<CardTitle>Basic Information</CardTitle>
							<CardDescription>Your personal details</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="grid gap-4 sm:grid-cols-2">
								<div className="space-y-2">
									<Label htmlFor="firstName">First name</Label>
									<Input
										id="firstName"
										type="text"
										value={formData.firstName}
										onChange={(event) => handleChange('firstName', event.target.value)}
										required
									/>
								</div>

								<div className="space-y-2">
									<Label htmlFor="lastName">Last name</Label>
									<Input
										id="lastName"
										type="text"
										value={formData.lastName}
										onChange={(event) => handleChange('lastName', event.target.value)}
										required
									/>
								</div>
							</div>
						</CardContent>
					</Card>

					<Card>
						<CardHeader>
							<CardTitle>Experience</CardTitle>
							<CardDescription>Your professional experience level</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="grid gap-4 sm:grid-cols-2">
								<div className="space-y-2">
									<Label htmlFor="experienceLevel">Experience level</Label>
									<Select
										value={formData.experienceLevel}
										onValueChange={(value) => handleChange('experienceLevel', value)}
									>
										<SelectTrigger id="experienceLevel">
											<SelectValue placeholder="Select level" />
										</SelectTrigger>
										<SelectContent>
											{EXPERIENCE_OPTIONS.map((option) => (
												<SelectItem key={option.value} value={option.value}>
													{option.label}
												</SelectItem>
											))}
										</SelectContent>
									</Select>
								</div>

								<div className="space-y-2">
									<Label htmlFor="yearsOfExperience">Years of experience</Label>
									<Input
										id="yearsOfExperience"
										type="number"
										min="0"
										max="50"
										value={formData.yearsOfExperience}
										onChange={(event) => handleChange('yearsOfExperience', event.target.value)}
									/>
								</div>
							</div>
						</CardContent>
					</Card>

					<Card>
						<CardHeader>
							<CardTitle>Skills</CardTitle>
							<CardDescription>Add your technical and professional skills</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="flex gap-2">
								<Input
									type="text"
									placeholder="e.g., React, Python, Project Management"
									value={newSkill}
									onChange={(event) => setNewSkill(event.target.value)}
									onKeyDown={(event) => {
										if (event.key === 'Enter') {
											event.preventDefault();
											addSkill();
										}
									}}
								/>
								<Button type="button" onClick={addSkill} disabled={!newSkill.trim()}>
									<Plus className="mr-2 h-4 w-4" />
									Add
								</Button>
							</div>

							{skills.length > 0 ? (
								<div className="flex flex-wrap gap-2">
									{skills.map((skill) => (
										<Badge key={skill} variant="secondary" className="py-1.5 pl-3 pr-1">
											{skill}
											<button
												type="button"
												onClick={() => removeSkill(skill)}
												className="ml-2 rounded-full p-0.5 hover:bg-neutral-200"
											>
												<X className="h-3 w-3" />
											</button>
										</Badge>
									))}
								</div>
							) : (
								<p className="text-sm italic text-neutral-500">
									No skills added yet. Add your first skill above.
								</p>
							)}
						</CardContent>
					</Card>

					<Card>
						<CardHeader>
							<CardTitle>Areas of Interest</CardTitle>
							<CardDescription>Topics and industries you're interested in</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="flex gap-2">
								<Input
									type="text"
									placeholder="e.g., Artificial Intelligence, Healthcare, Education"
									value={newInterest}
									onChange={(event) => setNewInterest(event.target.value)}
									onKeyDown={(event) => {
										if (event.key === 'Enter') {
											event.preventDefault();
											addInterest();
										}
									}}
								/>
								<Button type="button" onClick={addInterest} disabled={!newInterest.trim()}>
									<Plus className="mr-2 h-4 w-4" />
									Add
								</Button>
							</div>

							{interests.length > 0 ? (
								<div className="flex flex-wrap gap-2">
									{interests.map((interest) => (
										<Badge key={interest} variant="secondary" className="py-1.5 pl-3 pr-1">
											{interest}
											<button
												type="button"
												onClick={() => removeInterest(interest)}
												className="ml-2 rounded-full p-0.5 hover:bg-neutral-200"
											>
												<X className="h-3 w-3" />
											</button>
										</Badge>
									))}
								</div>
							) : (
								<p className="text-sm italic text-neutral-500">
									No interests added yet. Add your first interest above.
								</p>
							)}
						</CardContent>
					</Card>

					<Card>
						<CardHeader>
							<CardTitle>Bio</CardTitle>
							<CardDescription>Share a quick summary about yourself</CardDescription>
						</CardHeader>
						<CardContent>
							<Textarea
								value={formData.bio}
								onChange={(event) => handleChange('bio', event.target.value)}
								placeholder="Tell us about your experience and goals..."
							/>
						</CardContent>
					</Card>

					<div className="flex items-center justify-end gap-4 pt-4">
						<Button type="button" variant="outline" onClick={() => window.history.back()}>
							Cancel
						</Button>
						<Button type="submit" disabled={isLoading}>
							{isLoading ? (
								<>
									   <Spinner size={18} className="mr-2" />
									Saving...
								</>
							) : (
								'Save profile'
							)}
						</Button>
					</div>
				</form>
			</div>
		</div>
	);
};

export default Profile;
