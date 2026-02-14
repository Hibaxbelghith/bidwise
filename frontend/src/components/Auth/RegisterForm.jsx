import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import './AuthForms.css';

const RegisterForm = () => {
	const [formData, setFormData] = useState({
		email: '',
		username: '',
		first_name: '',
		last_name: '',
		account_type: 'CANDIDAT',
		password: '',
		password2: '',
	});
	const [formError, setFormError] = useState('');
	const { register, loading, error } = useAuth();
	const navigate = useNavigate();

	const handleChange = (event) => {
		const { name, value } = event.target;
		setFormData((prev) => ({ ...prev, [name]: value }));
	};

	const handleSubmit = async (event) => {
		event.preventDefault();
		setFormError('');

		if (
			!formData.email ||
			!formData.username ||
			!formData.first_name ||
			!formData.last_name ||
			!formData.password ||
			!formData.password2
		) {
			setFormError('Veuillez remplir tous les champs.');
			return;
		}

		if (formData.password !== formData.password2) {
			setFormError('Les mots de passe ne correspondent pas.');
			return;
		}

		const result = await register(formData);
		if (result.success) {
			navigate('/login');
		}
	};

	return (
		<div className="auth-container">
			<div className="auth-shell">
				<div className="auth-panel">
					<p className="auth-kicker">BidWise</p>
					<h1 className="auth-hero">Creez votre espace</h1>
					<p className="auth-lead">
						Rejoignez la plateforme et commencez a gerer vos opportunites des aujourd'hui.
					</p>
					<ul className="auth-list">
						<li>Un compte candidat ou organisation</li>
						<li>Acces immediat aux fonctionnalites</li>
						<li>Un seul profil pour web et mobile</li>
					</ul>
				</div>

				<form className="auth-card" onSubmit={handleSubmit}>
					<h2 className="auth-title">Inscription</h2>

				<label className="auth-label" htmlFor="register-email">
					Email
				</label>
				<input
					id="register-email"
					className="auth-input"
					type="email"
					name="email"
					placeholder="ex: user@email.com"
					value={formData.email}
					onChange={handleChange}
				/>

				<label className="auth-label" htmlFor="register-username">
					Username
				</label>
				<input
					id="register-username"
					className="auth-input"
					type="text"
					name="username"
					placeholder="ex: john_doe"
					value={formData.username}
					onChange={handleChange}
				/>

				<div className="auth-row">
					<div className="auth-col">
						<label className="auth-label" htmlFor="register-first-name">
							Prénom
						</label>
						<input
							id="register-first-name"
							className="auth-input"
							type="text"
							name="first_name"
							placeholder="Prénom"
							value={formData.first_name}
							onChange={handleChange}
						/>
					</div>

					<div className="auth-col">
						<label className="auth-label" htmlFor="register-last-name">
							Nom
						</label>
						<input
							id="register-last-name"
							className="auth-input"
							type="text"
							name="last_name"
							placeholder="Nom"
							value={formData.last_name}
							onChange={handleChange}
						/>
					</div>
				</div>

				<label className="auth-label" htmlFor="register-account-type">
					Type de compte
				</label>
				<select
					id="register-account-type"
					className="auth-input"
					name="account_type"
					value={formData.account_type}
					onChange={handleChange}
				>
					<option value="CANDIDAT">Candidat</option>
					<option value="ORGANISATION">Organisation</option>
				</select>

				<div className="auth-row">
					<div className="auth-col">
						<label className="auth-label" htmlFor="register-password">
							Mot de passe
						</label>
						<input
							id="register-password"
							className="auth-input"
							type="password"
							name="password"
							placeholder="Mot de passe"
							value={formData.password}
							onChange={handleChange}
						/>
					</div>

					<div className="auth-col">
						<label className="auth-label" htmlFor="register-password2">
							Confirmation
						</label>
						<input
							id="register-password2"
							className="auth-input"
							type="password"
							name="password2"
							placeholder="Confirmer"
							value={formData.password2}
							onChange={handleChange}
						/>
					</div>
				</div>

				{(formError || error) && (
					<p className="auth-error">{formError || error}</p>
				)}

					<button className="auth-button" type="submit" disabled={loading}>
						{loading ? 'Inscription...' : 'Creer un compte'}
					</button>
				</form>
			</div>
		</div>
	);
};

export default RegisterForm;
