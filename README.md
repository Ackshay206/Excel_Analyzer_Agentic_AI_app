# Excel Analyzer - Agentic AI Application

An intelligent Excel file analyzer powered by AI agents that allows users to query billing data using natural language. Built with FastAPI backend and React frontend, leveraging LangChain and OpenAI's GPT models for intelligent data analysis.

## Features

- **Natural Language Queries**: Ask questions about your Excel data in plain English
- **Caching**: Session-based caching for faster response times
- **Custom API Keys**: Use your own OpenAI API key or the default one
- **File Management**: Easy upload, view, and delete multiple Excel files
- **Reasoning Transparency**: See the AI's step-by-step reasoning process
- **ReAct Agent Architecture**: Intelligent agents that think, act, and reason

## Architecture

### Backend (FastAPI + LangChain)
- **FastAPI**: Modern Python web framework for building APIs
- **LangChain**: Framework for developing AI agent applications
- **Pandas**: Data manipulation and analysis
- **OpenAI GPT-4**: Large language model for natural language understanding

### Frontend (React + Vite)
- **React 18**: Modern UI library
- **Vite**: Lightning-fast build tool
- **CSS3**: Custom styling with gradient themes

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **Node.js 18+** and npm ([Download](https://nodejs.org/))
- **Git** 
- **OpenAI API Key** ([Get one here](https://platform.openai.com/api-keys))

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Ackshay206/Excel_Analyzer_Agentic_AI_app.git
cd Excel_Analyzer_Agentic_AI_app
```
### 2. Backend Setup

```bash 
cd backend 

#Install dependencies
pip install -r requirements.txt

#Create data directory
mkdir -p data/excel-files

#start the backend server
uvicorn app.main:app --reload
```

### 3.Frontend Setup

```bash 
#Go to project root
cd frontend

#install dependencies
npm install

#start the frontend server
npm run dev
```

## How to Use
#### Step 1: Open the Application

Navigate to http://localhost:5173 in your browser

#### Step 2: Set API Key 

Click "Set API Key" button in header
Enter your OpenAI API key (starts with sk-)
Click "Save"

#### Step 3: Upload Excel File

Click "Choose File" in File Management section
Select an Excel file (.xlsx or .xls)
Click "Upload File"

Excel File Requirements: Must be .xlsx or .xls format
Must contain a sheet named "Billing Invoice (BI) Detail"
Should have clear column headers

#### Step 4: Ask Questions
Select your uploaded file and type questions like:

Example Queries:

Using the February workbook, return the top ten 'agency hierarchy code' values ranked by their total 'line net amount'.

For the March file, calculate the average 'line net amount' for each 'agency hierarchy code' and return the three codes with the largest averages.

#### Step 5: View Results

Answer: Direct response to your query. 
Reasoning Process: AI's step-by-step thinking. 
Execution Time: Processing time. 