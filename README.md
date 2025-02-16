# Resume-Ranker-with-Azure-OpenAI

This project implements a RESTful API for automating resume ranking based on job descriptions using Azure OpenAI as the language model for natural language processing. Built with Flask, the application provides two main endpoints:

Extract Ranking Criteria (POST /extract-criteria):
Upload a job description (PDF/DOCX) to extract key ranking criteria such as skills, certifications, experience, and qualifications.

Score Resumes (POST /score-resumes):
Upload multiple resumes (PDF/DOCX) along with the extracted criteria to receive a scored evaluation. Each candidate is scored on individual criteria (0-5 scale), and the scores are aggregated into an Excel/CSV report.

Table of Contents
Features
Architecture
Requirements
Setup
Usage
Endpoints
1. Extract Criteria
2. Score Resumes
Example cURL Commands
Project Structure
Contribution Guidelines
License
Features
Azure OpenAI Integration: Uses Azure OpenAI (GPT4_Omni) for robust natural language processing.
File Handling: Supports PDF and DOCX file formats for both job descriptions and resumes.
Swagger UI Documentation: Automatically generated documentation with Flasgger.
Bulk Processing: Efficiently processes multiple resumes for automated scoring.
RESTful API: Easily deployable and scalable solution using Flask.
Architecture
Flask App: Hosts the two main endpoints.
LLM (Azure OpenAI):
Extracts key criteria from a job description.
Scores each resume against the provided criteria.
File Processing:
PDF extraction with PyPDF2.
DOCX extraction with python-docx.
Output:
JSON output for extracted criteria.
CSV output for the resume scoring.
Requirements
Python 3.8+
Packages:
Flask
flasgger
openai
PyPDF2
python-docx
Azure OpenAI API key and endpoint
Install dependencies with:

bash
Copy
pip install -r requirements.txt
(Ensure your requirements.txt includes the necessary libraries.)

Setup
Clone the Repository:

bash
Copy
git clone https://github.com/<your-username>/Resume-Ranker-with-Azure-OpenA.git
cd azure-openai-resume-ranking
Install Dependencies:

bash
Copy
pip install -r requirements.txt
Configure Azure OpenAI:

Set your Azure endpoint and API key in the code (or via environment variables).
Example:
python
Copy
endpoint = "https://<your-azure-endpoint>.openai.azure.com/"
api_key = "YOUR_AZURE_API_KEY"
deployment = "Your_model"
Run the Flask App:

bash
Copy
python app.py
The app will run on http://0.0.0.0:8038 by default (as per the code).

Access Swagger UI: Navigate to:

bash
Copy
http://localhost:8038/apidocs
to explore and test the endpoints.

Usage
Extract Ranking Criteria:

Upload a PDF/DOCX job description.
Receive a JSON response of extracted criteria.
Score Resumes:

Provide a JSON array of criteria.
Upload multiple PDF/DOCX resumes.
Receive a CSV file with candidate names and scores.
Endpoints
1. Extract Criteria
Method: POST /extract-criteria
Description: Extract ranking criteria from a job description file (PDF/DOCX).
Request:

file: The job description file.
Response (JSON):

json
Copy
{
  "criteria": [
    "Must have certification XYZ",
    "5+ years of experience in Python development",
    "Strong background in Machine Learning"
  ]
}
2. Score Resumes
Method: POST /score-resumes
Description: Score resumes based on provided ranking criteria.
Request:

criteria: A JSON list of criteria (e.g., ["Criterion1", "Criterion2"]).
files: One or more resume files (PDF/DOCX).
Response:

A CSV file with columns for Candidate Name, each criterion score, and the Total Score.
Example cURL Commands
Extract Criteria:

bash

curl -X POST "http://localhost:8038/extract-criteria" \
  -F "file=@/path/to/job_description.pdf"
Score Resumes:

bash

curl -X POST "http://localhost:8038/score-resumes" \
  -F 'criteria=["Must have certification XYZ", "5+ years of experience in Python development", "Strong background in Machine Learning"]' \
  -F "files=@/path/to/resume1.pdf" \
  -F "files=@/path/to/resume2.docx"






