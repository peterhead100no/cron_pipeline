import os
import json
from dotenv import load_dotenv
from openai import OpenAI
import psycopg2
from database import get_db_connection


def analyze_transcript_with_openai(transcript_text, client):
	"""
	Analyze transcript using OpenAI API with structured prompt.

	Args:
		transcript_text: The diarized transcript text
		client: OpenAI client instance

	Returns:
		Dictionary with analysis results
	"""
	if not transcript_text or transcript_text.strip() == "":
		return None

	prompt = f"""You are an expert call QA + triage analyst. Analyze the call transcript and return ONLY a valid JSON object.
Follow these rules strictly:
1) Output must be valid JSON with double quotes, no trailing commas, no markdown, no extra text.
2) Use ONLY the keys listed in the schema below (no additional keys).
3) Use only the allowed values for enum fields exactly as written.
4) If the transcript does not contain enough evidence to decide, use "Unclear" (do NOT guess).
5) Infer which speaker is "Call_Assistant" vs "Customer" from context .
6) For each classification field, include a short evidence snippet from the transcript (max 20 words) that supports it, or "" if Unclear.

Priority rules:
- "High" = safety risk, threats, urgent outage/payment loss, account locked, fraud, or user demands immediate resolution.
- "Medium" = user problem needs follow-up but not urgent (bug, confusion, standard support).
- "Low" = general inquiry, info request, no immediate action needed.

Threat rules:
- "Yes" only if explicit threat of violence, self-harm, legal threat, harassment, or credible intimidation.
- Otherwise "No" or "Unclear" if ambiguous.

Nuisance rules:
- "Yes" only if foul language, harassment, discriminatory slurs, or abusive behavior is present.

Satisfaction rules:
- "Yes" if customer explicitly satisfied/thanks/resolution confirmed.
- "No" if customer expresses dissatisfaction, unresolved complaint, or negative closing.
- "Unclear" if not enough closing signal.

Schema (return exactly these keys in json executable format ONLY):
{{
  "summary": "string (2-4 sentences, no assumptions)",

  "threat_flag": "Yes|No|Unclear",
  "threat_evidence": "string",

  "priority": "High|Medium|Low",
  "priority_reason": "string (1 sentence)",

  "human_intervention_required": "Yes|No|Unclear",
  "human_intervention_reason": "string",

  "satisfied": "Yes|No|Unclear",
  "satisfied_evidence": "string",

  "nuisance": "Yes|No|Unclear",
  "nuisance_evidence": "string",

  "frustration_level": "Low|Medium|High|Unclear",
  "frustration_evidence": "string",

  "repeated_complaint": "Yes|No|Unclear",
  "repeated_complaint_evidence": "string",

  "next_best_action": "string (single recommended next step)",
  "open_questions": ["string", "string"],

  "pii_detected": "Yes|No|Unclear",
  "pii_types": ["Email", "Phone", "Address", "Card", "Other", "None"]
}}

CALL TRANSCRIPT:
{transcript_text}

always return in json format strictly. dont want json in begining.
"""

	try:
		response = client.chat.completions.create(
			model="gpt-4o",
			messages=[{"role": "user", "content": prompt}],
			temperature=0.3,
		)

		response_text = response.choices[0].message.content.strip()

		# Remove markdown code block formatting if present
		if response_text.startswith("```json"):
			response_text = response_text[7:]
		elif response_text.startswith("```"):
			response_text = response_text[3:]

		if response_text.endswith("```"):
			response_text = response_text[:-3]

		response_text = response_text.strip()
		print(response_text)

		analysis = json.loads(response_text)
		return analysis

	except json.JSONDecodeError as e:
		print(f"Error parsing JSON response: {e}")
		return None
	except Exception as e:
		print(f"Error calling OpenAI API: {e}")
		return None


def restructure_analysis(analysis):
	"""
	Restructure the OpenAI response into the database format.

	Args:
		analysis: Raw analysis dictionary from OpenAI

	Returns:
		Restructured dictionary matching database schema
	"""
	structured = {
		"summary": analysis.get("summary", ""),
		"information_requested": analysis.get("information_requested", ""),

		"threat": {
			"flag": analysis.get("threat_flag", "Unclear"),
			"evidence": analysis.get("threat_evidence", "")
		},

		"priority": {
			"level": analysis.get("priority", "Low"),
			"reason": analysis.get("priority_reason", "")
		},

		"human_intervention": {
			"required": analysis.get("human_intervention_required", "Unclear"),
			"reason": analysis.get("human_intervention_reason", "")
		},

		"satisfaction": {
			"value": analysis.get("satisfied", "Unclear"),
			"evidence": analysis.get("satisfied_evidence", "")
		},

		"frustration": {
			"level": analysis.get("frustration_level", "Unclear"),
			"evidence": analysis.get("frustration_evidence", "")
		},

		"nuisance": {
			"value": analysis.get("nuisance", "No"),
			"evidence": analysis.get("nuisance_evidence", "")
		},

		"repeated_complaint": {
			"value": analysis.get("repeated_complaint", "No"),
			"evidence": analysis.get("repeated_complaint_evidence", "")
		},

		"pii_details": {
			"detected": analysis.get("pii_detected", "No"),
			"types": analysis.get("pii_types", ["None"])
		},

		"next_best_action": analysis.get("next_best_action", ""),
		"open_questions": analysis.get("open_questions", [])
	}

	return structured


def safe_delete(file_path: str) -> None:
	"""
	Delete a file safely (no crash if missing), and log the result.
	"""
	try:
		if os.path.exists(file_path):
			os.remove(file_path)
			print(f"🗑️ Deleted: {file_path}")
		else:
			print(f"⚠️ File not found (skip delete): {file_path}")
	except Exception as e:
		print(f"❌ Failed to delete {file_path}: {e}")


def main():
	load_dotenv()
	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		print("OPENAI_API_KEY not found in .env file.")
		return

	# Initialize OpenAI client
	client = OpenAI(api_key=api_key)

	# Folders
	audio_text_dir = "AUDIO_TO_TEXT"       # contains .txt transcripts
	audio_recording_dir = "AUDIO_RECORDING"  # contains .mp3 recordings
	input_dir = audio_text_dir
	output_dir = audio_text_dir  # where analysis JSON is saved

	# Connect to database
	connection = get_db_connection()
	if not connection:
		print("Failed to connect to database")
		return

	try:
		# Process all text files
		for filename in os.listdir(input_dir):
			if not filename.lower().endswith(".txt"):
				continue

			file_path = os.path.join(input_dir, filename)
			print(f"Processing: {filename}")

			# Get SID from filename (without extension)
			sid = os.path.splitext(filename)[0]

			# Read transcript file
			with open(file_path, "r", encoding="utf-8") as f:
				transcript_text = f.read()

			if not transcript_text.strip():
				print(f"✗ File is empty: {filename}\n")
				continue

			# Analyze with OpenAI
			analysis = analyze_transcript_with_openai(transcript_text, client)

			if not analysis:
				print(f"✗ Failed to analyze: {filename}\n")
				continue

			# Restructure analysis for database
			structured_analysis = restructure_analysis(analysis)

			# Save analysis as JSON file
			json_filename = f"{sid}_analysis.json"
			json_path = os.path.join(output_dir, json_filename)

			with open(json_path, "w", encoding="utf-8") as f:
				json.dump(structured_analysis, f, indent=2, ensure_ascii=False)

			# Update database with structured analysis
			cursor = connection.cursor()
			try:
				cursor.execute("""
					UPDATE public.exotel_data
					SET
						transcript = %s,
						summary = %s,
						information_requested = %s,
						threat = %s,
						priority = %s,
						human_intervention = %s,
						satisfaction = %s,
						frustration = %s,
						nuisance = %s,
						repeated_complaint = %s,
						next_best_action = %s,
						open_questions = %s,
						pii_details = %s,
						Completed = %s
					WHERE sid = %s
				""", (
					transcript_text,
					structured_analysis.get("summary", ""),
					structured_analysis.get("information_requested", ""),
					json.dumps(structured_analysis.get("threat", {})),
					json.dumps(structured_analysis.get("priority", {})),
					json.dumps(structured_analysis.get("human_intervention", {})),
					json.dumps(structured_analysis.get("satisfaction", {})),
					json.dumps(structured_analysis.get("frustration", {})),
					json.dumps(structured_analysis.get("nuisance", {})),
					json.dumps(structured_analysis.get("repeated_complaint", {})),
					structured_analysis.get("next_best_action", ""),
					json.dumps(structured_analysis.get("open_questions", [])),
					json.dumps(structured_analysis.get("pii_details", {})),
					True,
					sid
				))

				# IMPORTANT: commit before deleting files
				connection.commit()
				print(f"✓ Saved to: {json_path}")
				print(f"✓ Stored in database for SID: {sid}")

				# ✅ Delete processed files after success
				txt_file_path = os.path.join(audio_text_dir, filename)
				mp3_file_path = os.path.join(audio_recording_dir, f"{sid}.mp3")

				safe_delete(txt_file_path)
				safe_delete(mp3_file_path)
				safe_delete(json_path)  # Clean up JSON analysis file

				# Print analysis to console (optional)
				print("Analysis Results:")
				print(json.dumps(structured_analysis, indent=2, ensure_ascii=False))
				print()

			except psycopg2.Error as e:
				print(f"Database error while updating SID {sid}: {e}")
				connection.rollback()
				print("✗ Skipped deleting files due to DB failure.\n")
			finally:
				cursor.close()

	except psycopg2.Error as e:
		print(f"Database error: {e}")
		connection.rollback()
	finally:
		if connection:
			connection.close()
			print("Database connection closed")


if __name__ == "__main__":
	main()
