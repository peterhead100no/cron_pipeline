import os
import psycopg2
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from openai import OpenAI
import httpx
import time
import json

load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Exotel API credentials
EXOTEL_API_KEY = os.getenv("EXOTEL_API_KEY")
EXOTEL_API_TOKEN = os.getenv("EXOTEL_API_TOKEN")
EXOTEL_SID = os.getenv("EXOTEL_SID")
EXOTEL_SUBDOMAIN = "api.exotel.in"  # Standard Exotel subdomain

# OpenAI API credentials
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Build Base URL for Exotel API
BASE_URL = f"https://{EXOTEL_API_KEY}:{EXOTEL_API_TOKEN}@{EXOTEL_SUBDOMAIN}/v1/Accounts/{EXOTEL_SID}"


def get_incomplete_sids():
    """
    Fetch all SIDs from the crm-ai-db table where Completed is False
    
    Returns:
        list: A list of SID values where Completed = False
    """
    try:
        # Establish database connection
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Query to fetch all SIDs where Completed is False
        query = """SELECT sid FROM "crm-ai-db" WHERE "Completed" = FALSE and call_status = 'in-progress'"""
        cursor.execute(query)
        
        # Fetch all results
        results = cursor.fetchall()
        
        # Extract SIDs from results (results is a list of tuples)
        sids = [row[0] for row in results]
        
        cursor.close()
        conn.close()
        
        return sids
    
    except (Exception, psycopg2.Error) as error:
        print(f"Error while fetching data from PostgreSQL: {error}")
        return []


def get_call_info(call_sid):
    """
    Fetch call information from Exotel API (returns XML)
    
    Args:
        call_sid (str): The call SID to fetch information for
        
    Returns:
        dict: Parsed call information or None if failed
    """
    try:
        # Build the Exotel API URL using BASE_URL
        url = f"{BASE_URL}/Calls/{call_sid}"
        
        # Make the API request
        response = requests.get(url)
        
        if response.status_code == 200:
            try:
                # Parse XML response
                root = ET.fromstring(response.text)
                
                # Extract call data from XML
                call_data = {}
                call_element = root.find('Call')
                
                if call_element is not None:
                    for child in call_element:
                        call_data[child.tag] = child.text
                
                return call_data
            except ET.ParseError as e:
                print(f"Error parsing XML response for SID {call_sid}: {e}")
                print(f"Response text: {response.text}")
                return None
        else:
            print(f"Error fetching call info for SID {call_sid}: Status {response.status_code}")
            print(f"Response text: {response.text}")
            return None
    
    except Exception as error:
        print(f"Error while fetching call info from Exotel API: {error}")
        return None


def download_audio(recording_url, output_path):
    """
    Download audio file from recording URL with Exotel API authentication
    
    Args:
        recording_url (str): URL of the recording to download
        output_path (str): Local path to save the audio file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use Exotel API credentials for authentication
        auth = (EXOTEL_API_KEY, EXOTEL_API_TOKEN)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(recording_url, auth=auth, headers=headers, timeout=30)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded audio: {output_path}")
            return True
        else:
            print(f"Error downloading audio: Status {response.status_code}")
            print(f"Response: {response.text[:200] if response.text else 'No response body'}")
            return False
    
    except Exception as error:
        print(f"Error while downloading audio: {error}")
        return False


def make_openai_client(timeout_sec: float = 600) -> OpenAI:
    """Create OpenAI client with custom timeout"""
    return OpenAI(
        api_key=OPENAI_API_KEY,
        max_retries=0,
        timeout=httpx.Timeout(
            connect=10.0,
            read=timeout_sec,
            write=60.0,
            pool=10.0,
        ),
    )


def analyze_transcript_with_openai(transcript_text):
    """
    Analyze transcript using OpenAI API with structured prompt.

    Args:
        transcript_text: The transcript text

    Returns:
        Dictionary with analysis results
    """
    if not transcript_text or transcript_text.strip() == "":
        return None

    prompt = f"""
You are a senior call QA, compliance, and triage analyst.

Your task:
Analyze the call transcript and return ONLY a valid JSON object that strictly follows the schema and rules below.
 - Do NOT use Unicode escape sequences (e.g. \\uXXXX)
========================
ABSOLUTE OUTPUT RULES
========================
1) Output MUST be valid JSON only.
   - Use double quotes only
   - No markdown
   - No comments
   - No trailing commas
   - No text before or after the JSON

2) Use ONLY the keys listed in the schema.
   - No extra keys
   - No missing keys

3) Enum fields MUST use one of the allowed values EXACTLY as written.
   - If evidence is insufficient, use "Unclear"
   - Do NOT guess or infer without evidence

4) Every classification field MUST include:
   - A short direct quote from the transcript (max 20 words) as evidence
   - OR "" ONLY if the value is "Unclear"

5) Evidence MUST be verbatim or lightly trimmed from the transcript.
   - Do NOT paraphrase evidence
   - Do NOT fabricate quotes

6) CRITICAL — HUMAN READABLE TEXT ONLY:
   - Output MUST be human-readable UTF-8 text
   - Do NOT use Unicode escape sequences (e.g. \\uXXXX)
   - Hindi or other non-English text MUST be rendered directly (e.g. "मैं शिकायत करूँगा")
   - Any use of \\uXXXX makes the output INVALID

7) If any rule above is violated, the output is invalid.

========================
SPEAKER INFERENCE
========================
- Infer speakers from context.
- "Customer" = person seeking help or raising an issue.
- "Call_Assistant" = agent, IVR, support rep, or automated system.

========================
THREAT CLASSIFICATION (CRITICAL)
========================
Set "threat_flag" = "Yes" ONLY if the customer explicitly mentions ANY of the following:
- Police complaint / FIR / calling police
- Legal action / lawsuit / court case / lawyer
- Reporting to regulators, government, or media
- Violence, self-harm, or harm to others
- Harassment or intimidation threats

Examples that MUST be "Yes":
- "I will file a police complaint"
- "I am going to court"
- "My lawyer will contact you"
- "मैं पुलिस में शिकायत करूँगा"

Indirect, emotional, or vague language → "Unclear"
No threat language → "No"

========================
PRIORITY RULES
========================
High:
- Safety risk
- Legal or police threats
- Account locked or fraud
- Payment loss
- Customer demands immediate resolution

Medium:
- Issue requires follow-up
- Bugs, confusion, service problems

Low:
- General inquiry
- Information request only

========================
NUISANCE RULES
========================
Set "nuisance" = "Yes" ONLY if transcript contains:
- Profanity
- Harassment
- Abusive language
- Discriminatory or personal attacks

Complaints alone ≠ nuisance.

========================
SATISFACTION RULES
========================
Yes:
- Explicit thanks
- Issue confirmed resolved
- Positive closing statement

No:
- Complaint or frustration at end
- Issue unresolved
- Negative or angry closing

Unclear:
- No clear closing signal

========================
FRUSTRATION RULES
========================
High:
- Anger, threats, repeated complaints

Medium:
- Repeated concern, impatience

Low:
- Calm, neutral, cooperative

========================
PII RULES
========================
Detect ONLY if explicitly spoken in the transcript.
Do NOT assume or infer PII.

========================
SCHEMA (RETURN EXACTLY)
========================
{{
  "summary": "string (detailed, factual, no assumptions)",
  "information_requested": "string",
  "threat_flag": "Yes|No|Unclear",
  "threat_reason": "string",
  "priority": "High|Medium|Low",
  "priority_reason": "string",
  "human_intervention_required": "Yes|No|Unclear",
  "human_intervention_reason": "string",
  "satisfied": "Yes|No|Unclear",
  "satisfied_reason": "string",
  "nuisance": "Yes|No|Unclear",
  "nuisance_reason": "string",
  "frustration_level": "Low|Medium|High|Unclear",
  "frustration_reason": "string",
  "repeated_complaint": "Yes|No|Unclear",
  "repeated_complaint_reason": "string",
  "next_best_action": "string (single clear next step)",
  "open_questions": ["string", "string"],
  "pii_detected": "Yes|No|Unclear",
  "pii_types": ["Email", "Phone", "Address", "Card", "Other", "None"]
}}

========================
CALL TRANSCRIPT
========================
{transcript_text}

Return JSON ONLY.
"""



    try:
        client = make_openai_client()
        response = client.chat.completions.create(
            model="gpt-4.1",
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
        print(f"✓ Analysis response received")

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
            "reason": analysis.get("threat_reason", "")
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
            "reason": analysis.get("satisfied_reason", "")
        },

        "frustration": {
            "level": analysis.get("frustration_level", "Unclear"),
            "reason": analysis.get("frustration_reason", "")
        },

        "nuisance": {
            "value": analysis.get("nuisance", "No"),
            "reason": analysis.get("nuisance_reason", "")
        },

        "repeated_complaint": {
            "value": analysis.get("repeated_complaint", "No"),
            "reason": analysis.get("repeated_complaint_reason", "")
        },

        "pii_details": {
            "detected": analysis.get("pii_detected", "No"),
            "types": analysis.get("pii_types", ["None"])
        },

        "next_best_action": analysis.get("next_best_action", ""),
        "open_questions": analysis.get("open_questions", [])
    }

    return structured



def transcribe_audio(audio_path):
    """
    Transcribe audio file using OpenAI API
    
    Args:
        audio_path (str): Path to the audio file
        
    Returns:
        str: Transcribed text or None if failed
    """
    try:
        client = make_openai_client()
        
        with open(audio_path, 'rb') as f:
            response = client.audio.transcriptions.create(
                file=f,
                model="whisper-1",
                response_format="text",
            )
        
        print(f"✓ Transcribed audio: {audio_path}")
        return response
    
    except Exception as error:
        print(f"Error while transcribing audio: {error}")
        return None


def save_call_status_to_db(call_sid, call_status):
    """
    Save call status to the database
    
    Args:
        call_sid (str): The call SID
        call_status (str): Status of the call (e.g., 'completed', 'failed')
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Update the crm-ai-db table with call status only
        update_query = '''
            UPDATE "crm-ai-db" 
            SET 
                call_status = %s
            WHERE sid = %s
        '''
        
        cursor.execute(update_query, (call_status, call_sid))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✓ Saved call status to database for SID: {call_sid}")
        return True
    
    except (Exception, psycopg2.Error) as error:
        print(f"Error while saving call status to database: {error}")
        return False


def save_transcript_to_db(call_sid, transcript_text, transcript_status="completed", mark_completed=False):
    """
    Save transcript details to the database
    
    Args:
        call_sid (str): The call SID
        transcript_text (str): The transcribed text
        transcript_status (str): Status of transcription (completed, failed, etc.)
        mark_completed (bool): Whether to mark Completed as TRUE (only on success)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Update the crm-ai-db table with transcript details
        if mark_completed:
            update_query = '''
                UPDATE "crm-ai-db" 
                SET 
                    transcript = %s,
                    transcript_status = %s,
                    "Completed" = %s
                WHERE sid = %s
            '''
            cursor.execute(update_query, (transcript_text, transcript_status, True, call_sid))
        else:
            update_query = '''
                UPDATE "crm-ai-db" 
                SET 
                    transcript = %s,
                    transcript_status = %s
                WHERE sid = %s
            '''
            cursor.execute(update_query, (transcript_text, transcript_status, call_sid))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print(f"✓ Saved transcript to database for SID: {call_sid}")
        return True
    
    except (Exception, psycopg2.Error) as error:
        print(f"Error while saving transcript to database: {error}")
        return False


def save_structured_analysis_to_db(call_sid, transcript_text, structured_analysis):
    """
    Save structured analysis data to the database
    
    Args:
        call_sid (str): The call SID
        transcript_text (str): The transcribed text
        structured_analysis (dict): Dictionary containing analysis results
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        cursor = conn.cursor()
        
        # Prepare data with JSON serialization for complex fields
        update_query = '''
            UPDATE "crm-ai-db" 
            SET 
                transcript = %s,
                transcript_status = %s,
                summary = %s,
                summary_completed = %s,
                information_requested = %s,
                information_requested_completed = %s,
                threat = %s,
                threat_completed = %s,
                priority = %s,
                priority_completed = %s,
                human_intervention = %s,
                human_intervention_completed = %s,
                satisfaction = %s,
                satisfaction_completed = %s,
                frustration = %s,
                frustration_completed = %s,
                nuisance = %s,
                nuisance_completed = %s,
                repeated_complaint = %s,
                repeated_complaint_completed = %s,
                next_best_action = %s,
                next_best_action_completed = %s,
                open_questions = %s,
                open_questions_completed = %s,
                pii_details = %s,
                pii_details_completed = %s,
                "Completed" = %s
            WHERE sid = %s
        '''
        
        cursor.execute(update_query, (
            transcript_text,
            "completed",
            structured_analysis.get("summary", ""),
            True,
            structured_analysis.get("information_requested", ""),
            True,
            json.dumps(structured_analysis.get("threat", {})),
            True,
            json.dumps(structured_analysis.get("priority", {})),
            True,
            json.dumps(structured_analysis.get("human_intervention", {})),
            True,
            json.dumps(structured_analysis.get("satisfaction", {})),
            True,
            json.dumps(structured_analysis.get("frustration", {})),
            True,
            json.dumps(structured_analysis.get("nuisance", {})),
            True,
            json.dumps(structured_analysis.get("repeated_complaint", {})),
            True,
            structured_analysis.get("next_best_action", ""),
            True,
            json.dumps(structured_analysis.get("open_questions", [])),
            True,
            json.dumps(structured_analysis.get("pii_details", {})),
            True,
            True,
            call_sid
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✓ Saved structured analysis to database for SID: {call_sid}")
        return True
    
    except (Exception, psycopg2.Error) as error:
        print(f"Error while saving structured analysis to database: {error}")
        return False


def process_incomplete_calls():
    """
    Fetch all incomplete SIDs, get call information, download recordings,
    transcribe them, and save results to database
    """
    # Get all incomplete SIDs from database
    sids = get_incomplete_sids()
    
    if not sids:
        print("No incomplete SIDs found")
        return
    
    print(f"Processing {len(sids)} incomplete calls...\n")
    
    # Create directory for audio files if it doesn't exist
    os.makedirs("AUDIO_DOWNLOADS", exist_ok=True)
    
    # Process each SID
    for idx, sid in enumerate(sids, 1):
        print(f"\n[{idx}/{len(sids)}] Processing SID: {sid}")
        print("-" * 60)
        
        try:
            # Step 1: Fetch call info from Exotel API
            print(f"  Step 1: Fetching call info...")
            call_info = get_call_info(sid)
            
            if not call_info:
                print(f"  ✗ Failed to fetch call info for SID: {sid}")
                print(f"  ℹ No database changes made")
                continue
            
            # Extract call status and recording URL
            call_status = call_info.get('Status')
            print(f"  ℹ Call Status: {call_status}")
            
            # Step 2: Extract recording URL
            recording_url = call_info.get('RecordingUrl')
            if not recording_url:
                print(f"  ✗ No recording URL found for SID: {sid}")
                print(f"  ℹ Skipping processing - No database changes made (Completed remains FALSE)")
                continue
            
            print(f"  ✓ Recording URL found")
            
            # Step 3: Download audio file
            print(f"  Step 2: Downloading audio...")
            audio_filename = f"AUDIO_DOWNLOADS/{sid}.mp3"
            
            if not download_audio(recording_url, audio_filename):
                print(f"  ✗ Failed to download audio for SID: {sid}")
                print(f"  ℹ No database changes made")
                continue
            
            # Step 4: Transcribe audio
            print(f"  Step 3: Transcribing audio...")
            transcript_text = transcribe_audio(audio_filename)
            
            if not transcript_text:
                print(f"  ✗ Failed to transcribe audio for SID: {sid}")
                print(f"  ℹ No database changes made")
                continue
            
            print(f"  ✓ Transcript generated: {len(transcript_text)} characters")
            
            # Step 5: Analyze transcript with OpenAI
            print(f"  Step 4: Analyzing transcript...")
            analysis = analyze_transcript_with_openai(transcript_text)
            
            if not analysis:
                print(f"  ✗ Failed to analyze transcript for SID: {sid}")
                print(f"  ℹ No database changes made")
                continue
            
            # Restructure analysis for database
            structured_analysis = restructure_analysis(analysis)
            print(f"  ✓ Analysis completed")
            
            # Step 6: Save to database ONLY if all steps succeeded
            print(f"  Step 5: Saving all data to database...")
            if save_call_status_to_db(sid, call_status) and save_structured_analysis_to_db(sid, transcript_text, structured_analysis):
                print(f"  ✓ Successfully processed and saved SID: {sid}")
                
                # Step 7: Delete audio file after successful processing
                print(f"  Step 6: Cleaning up audio file...")
                try:
                    if os.path.exists(audio_filename):
                        os.remove(audio_filename)
                        print(f"  ✓ Deleted audio file: {audio_filename}")
                except Exception as e:
                    print(f"  ⚠ Failed to delete audio file: {e}")
            else:
                print(f"  ✗ Failed to save data for SID: {sid}")
                print(f"  ℹ Database rollback - no data was saved")
        
        except Exception as e:
            print(f"  ✗ Unexpected error processing SID {sid}: {e}")
            print(f"  ℹ No database changes made")
        
        # Small delay between requests
        time.sleep(1)


if __name__ == "__main__":
    # Run the main processing loop
    process_incomplete_calls()
