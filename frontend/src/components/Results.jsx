import React from 'react';

export default function Results({ result }) {
  if (!result) return null;

  return (
    <div className="results">
      <div className="card metric-card">
        <div className="metric">
          <span className="metric-label">Execution Time</span>
          <span className="metric-value">{result.execution_time}s</span>
        </div>
      </div>

      <div className="card answer-card">
        <h3 className="section-title">Answer</h3>
        <div className="answer-content">{result.answer}</div>
      </div>

      {result.reasoning && (
        <div className="card reasoning-card">
          <h3 className="section-title">Reasoning Process</h3>
          <pre className="reasoning-content">{result.reasoning}</pre>
        </div>
      )}
    </div>
  );
}
