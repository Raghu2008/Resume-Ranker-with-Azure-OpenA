import json
import io
import csv
import re
import traceback

from flask import Flask, request, jsonify, make_response
from flasgger import Swagger, swag_from
from PyPDF2 import PdfReader
import docx

import openai
from openai import AzureOpenAI



# Azure OpenAI configuration
endpoint = "https://<Your_domain>.openai.azure.com/"
api_key = "YOUR_AZURE_API_KEY"
deployment = "Your_model"

client = openai.AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=api_key,
    api_version="2024-02-01",
)

app = Flask(__name__)
swagger = Swagger(app)


def extract_text_from_file(file_storage):
    """
    Extract text from a PDF or DOCX file.
    """
    filename = file_storage.filename.lower()
    text = ""
    if filename.endswith(".pdf"):
        try:
            pdf_reader = PdfReader(file_storage)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        except Exception as e:
            app.logger.error(f"Error reading PDF: {e}")
            text = f"Error reading PDF: {e}"
    elif filename.endswith(".docx"):
        try:
            doc = docx.Document(file_storage)
            for para in doc.paragraphs:
                text += para.text + "\n"
        except Exception as e:
            app.logger.error(f"Error reading DOCX: {e}")
            text = f"Error reading DOCX: {e}"
    else:
        text = "Unsupported file format."
    return text


def strip_markdown_fences(text):
    """
    Remove markdown code fences (e.g., ```json) from the beginning and end.
    """
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines)


def remove_json_comments(text):
    """
    Remove inline JSON comments (// comments) from the text.
    """
    return re.sub(r'//.*$', '', text, flags=re.MULTILINE)


def clean_llm_response(text):
    """
    Clean the LLM response by stripping markdown fences and removing inline JSON comments.
    """
    text = strip_markdown_fences(text)
    text = remove_json_comments(text)
    return text.strip()


def extract_criteria_llm(job_description_text):
    """
    Calls Azure OpenAI to extract ranking criteria from job description text.
    """
    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant for extracting ranking criteria from job descriptions."
        },
        {
            "role": "user",
            "content": (
                f"Extract key ranking criteria such as skills, certifications, experience, "
                f"and qualifications from the following job description. Provide the results as a JSON list of strings.\n\n"
                f"Job Description:\n{job_description_text}"
            )
        }
    ]

    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
        )
        response = completion.choices[0].message.content
        app.logger.debug("LLM response for extract_criteria_llm: " + response)
        cleaned_response = clean_llm_response(response)
        try:
            criteria = json.loads(cleaned_response)
        except Exception as parse_error:
            app.logger.error("Error parsing LLM response as JSON: " + str(parse_error))
            # Fallback: split lines if JSON parsing fails
            criteria = [line.strip() for line in cleaned_response.splitlines() if line.strip()]
        return criteria
    except Exception as e:
        app.logger.error("Error calling extract_criteria_llm: " + str(e))
        app.logger.error(traceback.format_exc())
        return []


def score_resume_llm(resume_text, criteria):
    """
    Calls Azure OpenAI to score a resume based on the provided criteria.
    Expects a JSON response in the following format:
    {
      "candidate_name": "Extracted Name",
      "scores": [score1, score2, ...]
    }
    """
    prompt = "Evaluate the following resume against these ranking criteria.\n\nCriteria:\n"
    for idx, crit in enumerate(criteria, 1):
        prompt += f"{idx}. {crit}\n"
    prompt += "\nResume Text:\n" + resume_text
    prompt += (
        "\n\nFor each criterion, assign a score from 0 (not present) to 5 (fully matches). "
        "Extract the candidate's name if available. Return a JSON object in the following format:\n"
        '{"candidate_name": "Name", "scores": [score1, score2, ...]}'
    )

    messages = [
        {
            "role": "system",
            "content": "You are an AI assistant for evaluating resumes."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]

    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
        )
        response = completion.choices[0].message.content
        app.logger.debug("LLM response for score_resume_llm: " + response)
        cleaned_response = clean_llm_response(response)
        try:
            result = json.loads(cleaned_response)
        except Exception as parse_error:
            app.logger.error("Error parsing LLM response as JSON: " + str(parse_error))
            result = {"candidate_name": "Unknown", "scores": [0] * len(criteria)}
        return result
    except Exception as e:
        app.logger.error("Error in score_resume_llm: " + str(e))
        app.logger.error(traceback.format_exc())
        return {"candidate_name": "Unknown", "scores": [0] * len(criteria)}


@app.route("/extract-criteria", methods=["POST"])
@swag_from({
    "tags": ["Resume Ranking"],
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": True,
            "description": "Job description file (PDF or DOCX)"
        }
    ],
    "responses": {
        "200": {
            "description": "Extracted ranking criteria",
            "examples": {
                "application/json": {
                    "criteria": [
                        "Must have certification XYZ",
                        "5+ years of experience in Python development",
                        "Strong background in Machine Learning"
                    ]
                }
            }
        },
        "400": {
            "description": "Bad request. File not provided or invalid."
        }
    }
})
def extract_criteria():
    """Endpoint to extract ranking criteria from a job description file."""
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    job_description_text = extract_text_from_file(file)
    app.logger.debug("Job description text extracted.")
    criteria = extract_criteria_llm(job_description_text)
    return jsonify({"criteria": criteria})


@app.route("/score-resumes", methods=["POST"])
@swag_from({
    "tags": ["Resume Ranking"],
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "criteria",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "A JSON list of ranking criteria. E.g., [\"criteria 1\", \"criteria 2\"]"
        },
        {
            "name": "files",
            "in": "formData",
            "type": "array",
            "items": {"type": "file"},
            "collectionFormat": "multi",
            "required": True,
            "description": "One or more resume files (PDF or DOCX)"
        }
    ],
    "responses": {
        "200": {
            "description": "CSV file containing candidate scores",
            "schema": {
                "type": "file"
            }
        },
        "400": {
            "description": "Bad request. Missing criteria or files."
        },
        "500": {
            "description": "Internal Server Error."
        }
    }
})
def score_resumes():
    """Endpoint to score resumes against provided ranking criteria and return a CSV report."""
    try:
        # Retrieve criteria from form field or file upload
        criteria_json = None
        if "criteria" in request.form:
            criteria_json = request.form["criteria"]
        elif "criteria" in request.files:
            criteria_file = request.files["criteria"]
            criteria_json = criteria_file.read().decode("utf-8")
        else:
            return jsonify({"error": "Criteria not provided"}), 400

        app.logger.debug("Received criteria JSON: " + criteria_json)

        try:
            criteria = json.loads(criteria_json)
        except Exception as e:
            app.logger.error("Error parsing criteria JSON: " + str(e))
            return jsonify({"error": f"Criteria must be a valid JSON list. Error: {e}"}), 400

        if "files" not in request.files:
            return jsonify({"error": "No resume files provided"}), 400

        resume_files = request.files.getlist("files")
        results = []
        for file in resume_files:
            app.logger.debug("Processing file: " + file.filename)
            resume_text = extract_text_from_file(file)
            app.logger.debug(f"Extracted resume text for {file.filename}")
            score_data = score_resume_llm(resume_text, criteria)
            candidate_name = score_data.get("candidate_name", "Unknown")
            scores = score_data.get("scores", [0] * len(criteria))
            total_score = sum(scores)
            results.append({
                "candidate_name": candidate_name,
                "scores": scores,
                "total_score": total_score
            })

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        header = ["Candidate Name"] + [f"Criterion {i+1}" for i in range(len(criteria))] + ["Total Score"]
        writer.writerow(header)
        for res in results:
            row = [res["candidate_name"]] + res["scores"] + [res["total_score"]]
            writer.writerow(row)
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=candidate_scores.csv"
        response.headers["Content-Type"] = "text/csv"
        return response

    except Exception as e:
        app.logger.error("Error in /score-resumes endpoint: " + str(e))
        app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal Server Error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8038, debug=True)
