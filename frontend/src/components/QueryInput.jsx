import React from 'react';

export default function QueryInput({ query, onQueryChange, onSubmit, loading }) {
  return (
    <div className="card">
      <h2 className="card-title">Ask a Question</h2>
      <textarea value={query} onChange={(e) => onQueryChange(e.target.value)} placeholder="What is the total billing amount?" className="textarea" rows="4" />
      <button onClick={onSubmit} disabled={loading || !query.trim()} className="btn-submit">
        {loading ? 'Processing...' : 'Submit Query'}
      </button>
    </div>
  );
}
