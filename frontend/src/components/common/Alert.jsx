import { useState, useEffect } from 'react';
import './Alert.css';

const Alert = ({ type = 'error', message, onClose, autoDismiss = false, duration = 5000 }) => {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (autoDismiss && duration > 0) {
      const timer = setTimeout(() => {
        setVisible(false);
        if (onClose) onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [autoDismiss, duration, onClose]);

  if (!visible || !message) return null;

  const icons = {
    error: '⚠️',
    success: '✅',
    info: 'ℹ️'
  };

  const handleClose = () => {
    setVisible(false);
    if (onClose) onClose();
  };

  return (
    <div className={`alert alert-${type}`}>
      <span className="alert-icon">{icons[type]}</span>
      <span>{message}</span>
      <button 
        type="button" 
        className="alert-close" 
        onClick={handleClose}
        aria-label="Fermer"
      >
        ×
      </button>
    </div>
  );
};

export default Alert;
