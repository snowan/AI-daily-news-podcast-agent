import os
from gtts import gTTS, gTTSError

# --- Configuration ---
PODCAST_SCRIPT_FILE = "data/podcast_script.txt"
OUTPUT_AUDIO_FILE = "data/podcast_audio.mp3"
LANGUAGE = 'en' # Language for TTS

# --- File Operations ---
def read_podcast_script(filepath: str) -> str | None:
    """Reads the content of the podcast script file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Successfully read podcast script from: {filepath}")
        # Basic cleaning: remove empty lines that might cause issues with TTS
        cleaned_content = "\n".join(line for line in content.splitlines() if line.strip())
        if not cleaned_content:
            print("Warning: Podcast script file is empty or contains only whitespace.")
            return None
        return cleaned_content
    except FileNotFoundError:
        print(f"Error: Podcast script file not found at {filepath}")
        return None
    except IOError as e:
        print(f"Error reading file {filepath}: {e}")
        return None

# --- Text-to-Speech Generation ---
def generate_audio_from_text(text_content: str, output_filepath: str, lang: str = LANGUAGE):
    """
    Converts the given text content to speech using gTTS and saves it as an MP3 file.
    """
    if not text_content:
        print("Error: No text content provided for TTS conversion.")
        return False
        
    print(f"\n--- Starting Text-to-Speech (gTTS) Conversion ---")
    print(f"Text to convert (first 100 chars): '{text_content[:100]}...'")
    print(f"Language: {lang}")
    
    try:
        # Create gTTS object
        tts = gTTS(text=text_content, lang=lang, slow=False)
        
        # Ensure the output directory exists
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        
        # Save the audio file
        tts.save(output_filepath)
        print(f"Audio successfully generated and saved to: {output_filepath}")
        return True
    except gTTSError as e:
        print(f"gTTS Error: Could not process the text. Details: {e}")
        print("This can happen due to network issues or problems with the input text (e.g., too long, unsupported characters for a language).")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during TTS generation or saving: {e}")
        return False

# --- Main Orchestration ---
def main():
    """
    Orchestrates reading the podcast script, generating audio, and saving it.
    """
    print("Starting podcast audio generation process...")

    # 1. Read Podcast Script
    script_text = read_podcast_script(PODCAST_SCRIPT_FILE)
    
    if script_text is None:
        print("Halting audio generation due to error reading podcast script or empty script.")
        return

    # 2. Generate Audio from Script Text
    success = generate_audio_from_text(script_text, OUTPUT_AUDIO_FILE)
    
    if success:
        print("\nPodcast audio generation process completed successfully.")
    else:
        print("\nPodcast audio generation process failed.")

if __name__ == "__main__":
    main()
