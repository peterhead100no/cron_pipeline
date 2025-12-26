
import os
import requests
from database import get_db_connection
from dotenv import load_dotenv

def fetch_and_download_recordings():
	load_dotenv()
	
	# Get Exotel credentials
	api_key = os.getenv("EXOTEL_API_KEY")
	api_token = os.getenv("EXOTEL_API_TOKEN")
	exotel_sid = os.getenv("EXOTEL_SID")
	
	if not api_key or not api_token or not exotel_sid:
		print("Missing Exotel credentials in .env file")
		return
	
	# Ensure output directory exists
	output_dir = 'AUDIO_RECORDING'
	os.makedirs(output_dir, exist_ok=True)

	# Connect to database
	conn = get_db_connection()
	if conn is None:
		print("Failed to connect to database.")
		return
	try:
		with conn.cursor() as cur:
			cur.execute("""
				SELECT sid, recordingurl 
				FROM public.exotel_data 
				WHERE recordingurl IS NOT NULL 
				AND recordingurl != ''
				AND (Completed IS NOT TRUE OR Completed IS NULL)
			""")
			rows = cur.fetchall()
			for sid, recordingurl in rows:
				if not recordingurl:
					continue
				filename = f"{sid}.mp3"
				filepath = os.path.join(output_dir, filename)
				try:
					# Use basic auth with API credentials
					response = requests.get(
						recordingurl,
						auth=(api_key, api_token),
						timeout=30
					)
					response.raise_for_status()
					with open(filepath, 'wb') as f:
						f.write(response.content)
					print(f"Downloaded: {filepath}")
				except Exception as e:
					print(f"Failed to download {recordingurl} for SID {sid}: {e}")
	finally:
		conn.close()

if __name__ == "__main__":
	fetch_and_download_recordings()
