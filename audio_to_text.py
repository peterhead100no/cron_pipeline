
#####$$$$$$$$$#######
import os
import time
import httpx
from dotenv import load_dotenv
from openai import OpenAI

# ==========================
# CONFIG
# ==========================
INPUT_DIR = "AUDIO_RECORDING"
OUTPUT_DIR = "AUDIO_TO_TEXT"

DIARIZE_MODEL = "gpt-4o-transcribe-diarize"
NORMAL_MODEL = "gpt-4o-mini-transcribe"   # or "gpt-4o-transcribe"

DIARIZE_TIMEOUT_SEC = 180  # 3 minutes
SLEEP_BETWEEN_FILES_SEC = 1

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==========================
# FORMATTERS
# ==========================
def format_diarized_text(tx):
    """
    diarized_json returns tx.segments with speaker labels. :contentReference[oaicite:4]{index=4}
    """
    if not tx or not getattr(tx, "segments", None):
        return getattr(tx, "text", "") or ""

    speaker_map = {}
    speaker_count = 1
    lines = []

    for seg in tx.segments:
        spk = getattr(seg, "speaker", "unknown")
        text = (getattr(seg, "text", "") or "").strip()
        if not text:
            continue

        if spk not in speaker_map:
            speaker_map[spk] = f"User {speaker_count}"
            speaker_count += 1

        lines.append(f"{speaker_map[spk]}: {text}")

    return "\n".join(lines).strip()


def format_normal_text(tx):
    # normal json transcription returns tx.text :contentReference[oaicite:5]{index=5}
    return (getattr(tx, "text", "") or "").strip()


# ==========================
# TRANSCRIPTION CALLS
# ==========================
def make_client(timeout_sec: float, api_key: str) -> OpenAI:
    # OpenAI Python SDK timeout support :contentReference[oaicite:6]{index=6}
    return OpenAI(
        api_key=api_key,
        max_retries=0,  # don't "hang" on hidden retries; we control fallback logic
        timeout=httpx.Timeout(
            connect=10.0,
            read=timeout_sec,
            write=60.0,
            pool=10.0,
        ),
    )


def transcribe_diarized(audio_path: str, api_key: str):
    client = make_client(DIARIZE_TIMEOUT_SEC, api_key)
    with open(audio_path, "rb") as f:
        return client.audio.transcriptions.create(
            file=f,
            model=DIARIZE_MODEL,
            response_format="diarized_json",   # required for speaker segments :contentReference[oaicite:7]{index=7}
            chunking_strategy="auto",          # recommended for diarization :contentReference[oaicite:8]{index=8}
        )


def transcribe_normal(audio_path: str, api_key: str):
    # Normal transcription: use mini model for speed/cost
    client = make_client(600, api_key)  # give it more time since it's the fallback
    with open(audio_path, "rb") as f:
        return client.audio.transcriptions.create(
            file=f,
            model=NORMAL_MODEL,
            response_format="json",            # supported output format :contentReference[oaicite:9]{index=9}
        )


# ==========================
# MAIN LOGIC
# ==========================
def process_file(filename: str, api_key: str):
    input_path = os.path.join(INPUT_DIR, filename)
    base_name = os.path.splitext(filename)[0]
    output_path = os.path.join(OUTPUT_DIR, f"{base_name}.txt")

    if os.path.exists(output_path):
        print(f"✓ Skipped (already exists): {filename}")
        return

    print(f"\nProcessing: {filename}")
    print("→ Attempting diarization (3 min timeout)")

    try:
        tx = transcribe_diarized(input_path, api_key)
        text = format_diarized_text(tx)

        if not text:
            raise RuntimeError("Empty diarized transcript")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"✓ Saved (diarized): {output_path}")
        return

    except (httpx.ReadTimeout, httpx.TimeoutException) as e:
        print(f"⚠ Diarization timed out after {DIARIZE_TIMEOUT_SEC}s. Falling back to normal transcription.")
    except Exception as e:
        print(f"⚠ Diarization failed ({type(e).__name__}: {e}). Falling back to normal transcription.")

    # Fallback path
    try:
        print("→ Normal transcription (no diarization)")
        tx2 = transcribe_normal(input_path, api_key)
        text2 = format_normal_text(tx2)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text2)

        print(f"✓ Saved (normal): {output_path}")

    except Exception as e:
        print(f"✗ Failed normal transcription: {filename} | {type(e).__name__}: {e}")


def main():
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY missing")
        return

    if not os.path.isdir(INPUT_DIR):
        print(f"❌ INPUT_DIR not found: {INPUT_DIR}")
        return

    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith((".mp3", ".wav", ".m4a"))]
    if not files:
        print("No audio files found")
        return

    print(f"Found {len(files)} audio files")

    for file in files:
        process_file(file, api_key)
        time.sleep(SLEEP_BETWEEN_FILES_SEC)


if __name__ == "__main__":
    main()
