import React, { useState } from 'react';

export default function Header({ 
  apiKeyStatus, 
  onSetApiKey, 
  onRemoveApiKey, 
  username, 
  onUsernameChange,
  isLoggedIn,
  onLogout 
}) {
  const [showInput, setShowInput] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [tempUsername, setTempUsername] = useState('');
  const [showUsernameInput, setShowUsernameInput] = useState(!isLoggedIn);

  const handleSave = async () => {
    if (!username && !tempUsername) {
      alert('Please enter a username');
      return;
    }
    if (!apiKey) {
      alert('Please enter an API key');
      return;
    }

    if (!isLoggedIn && tempUsername) {
      onUsernameChange(tempUsername);
    }
    
    await onSetApiKey(apiKey);
    setApiKey('');
    setShowInput(false);
    setShowUsernameInput(false);
  };

  return (
    <header className="header">
      <div className="header-content">
        <div className="logo-section">
          <div className="logo">$</div>
          <h1 className="title">BillingAnalyzer</h1>
        </div>

        <div className="user-controls">
          {isLoggedIn ? (
            <>
              <span className="user-badge">
                Signed in as: {username}
              </span>
              {apiKeyStatus && (
                <span className={`key-badge ${apiKeyStatus.using_custom_key ? 'custom' : 'default'}`}>
                  {apiKeyStatus.using_custom_key ? 'Custom Key' : 'Default Key'}
                </span>
              )}
              {apiKeyStatus?.using_custom_key && (
                <button onClick={onRemoveApiKey} className="btn-remove">Remove Key</button>
              )}
              <button onClick={() => setShowInput(!showInput)} className="btn-primary">
                {apiKeyStatus?.using_custom_key ? 'Change API Key' : 'Set API Key'}
              </button>
              <button onClick={onLogout} className="btn-logout">Logout</button>
            </>
          ) : (
            <button onClick={() => setShowUsernameInput(true)} className="btn-primary">
              Sign In
            </button>
          )}
        </div>
      </div>

      {showUsernameInput && !isLoggedIn && (
        <div className="login-section">
          <input
            type="text"
            value={tempUsername}
            onChange={(e) => setTempUsername(e.target.value)}
            placeholder="Enter username..."
            className="input"
          />
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter API key (sk-...)..."
            className="input"
          />
          <button onClick={handleSave} className="btn-save">Sign In</button>
        </div>
      )}

      {showInput && isLoggedIn && (
        <div className="api-input-section">
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="sk..."
            className="input"
          />
          <button onClick={handleSave} className="btn-save">Save</button>
        </div>
      )}
    </header>
  );
}
