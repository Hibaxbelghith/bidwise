import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext.jsx';
import Alert from '../common/Alert.jsx';
import './AuthForms.css';

const LoginForm = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [formError, setFormError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login, error } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');

    if (!username || !password) {
      setFormError('Veuillez remplir tous les champs.');
      return;
    }

    setIsLoading(true);
    const result = await login(username, password);
    setIsLoading(false);
    
    if (result.success) {
      navigate('/dashboard');
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-shell">
        <div className="auth-panel">
          <p className="auth-kicker">BidWise</p>
          <h1 className="auth-hero">Bienvenue, connectez-vous</h1>
          <p className="auth-lead">
            Accedez a vos opportunites et suivez vos candidatures en un seul endroit.
          </p>
          <ul className="auth-list">
            <li>Connexion securisee via JWT</li>
            <li>Profil centralise et a jour</li>
            <li>Acces rapide aux tableaux de bord</li>
          </ul>
        </div>

        <form className="auth-card" onSubmit={handleSubmit}>
          <h2 className="auth-title">Connexion</h2>

          {(formError || error) && (
            <Alert 
              type="error" 
              message={formError || error}
              onClose={() => setFormError('')}
            />
          )}

          <label className="auth-label" htmlFor="login-username">
            Email
          </label>
          <input
            id="login-username"
            className="auth-input"
            type="text"
            placeholder="ex: user@email.com"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={isLoading}
          />

          <label className="auth-label" htmlFor="login-password">
            Mot de passe
          </label>
          <input
            id="login-password"
            className="auth-input"
            type="password"
            placeholder="Votre mot de passe"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={isLoading}
          />

          <button className="auth-button" type="submit" disabled={isLoading}>
            {isLoading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginForm;
