import React from 'react';

export default function ErrorMessage({ error }) {
  if (!error) return null;
  return (
    <div className="error-card">
      <strong>Error:</strong> {error}
    </div>
  );
}
