import React from 'react';

export default function Instructions() {
  return (
    <div className="card instructions-card">
      <h3 className="section-title">Quick Start</h3>
      <ol className="instructions-list">
        <li>Set your OpenAI API key (optional)</li>
        <li>Select an Excel file</li>
        <li>Type your billing question</li>
        <li>Click Submit Query</li>
      </ol>
      <div className="examples">
        <strong>Example Questions:</strong>
        <ul>
          <li>What is the total billing amount?</li>
          <li>Show top 5 highest charges</li>
          <li>How many invoices are there?</li>
        </ul>
      </div>
    </div>
  );
}
