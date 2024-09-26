import speech_recognition as sr
from moviepy.editor import VideoFileClip
import os
from googletrans import Translator

video_file = input('Enter the path: ')
subtitle_file = r"D\\:/subtitles.srt"
output_file = r"D:/output_with_subtitle.mp4"


def transcription(video_path):
    """
    transcription for the videos and converting videos to audio format
    """
    try:
        # Convert video to audio
        video = VideoFileClip(video_path)
        audio_clip = video.audio
        audio_clip.write_audiofile('temp_audio.wav')

        # Transcribe audio
        recognizer = sr.Recognizer()
        with sr.AudioFile('temp_audio.wav') as source:
            audio_data = recognizer.record(source)
            transcript = recognizer.recognize_google(audio_data)

    finally:
        # Clean up
        if os.path.exists('temp_audio.wav'):
            os.remove('temp_audio.wav')

    return transcript


def translate_text(text, target_language='ar'):
    """
    translating the transcript of the videos
    """
    translator = Translator()
    try:
        result = translator.translate(text, dest=target_language)
        return result.text
    except Exception as e:
        print(f'An error occurred: {e}')
        return f'Error: {str(e)}'


def create_srt(translated_text, chunk_size=100):
    """
    Creates a subtitle (SRT) for the translated transcript, syncing with the video.
    All functionality is contained in one function.
    """
    # Load the video and get its duration
    video = VideoFileClip(video_file)
    video_duration = video.duration  # in seconds

    # Split the transcript into chunks based on words (instead of fixed characters)
    words = translated_text.split()
    lines = []
    current_chunk = []

    for word in words:
        if len(' '.join(current_chunk + [word])) <= chunk_size:
            current_chunk.append(word)
        else:
            lines.append(' '.join(current_chunk))
            current_chunk = [word]
    if current_chunk:
        lines.append(' '.join(current_chunk))

    # Calculate duration per subtitle (even distribution over the video)
    subtitle_duration = video_duration / len(lines)

    # Function to format time to SRT format (HH:MM:SS,ms)
    def format_time(seconds):
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    # Write to SRT format
    with open('D:/subtitles.srt', "w", encoding="utf-8") as srt_file:
        for i, line in enumerate(lines, 1):
            start_time = subtitle_duration * (i - 1)
            end_time = subtitle_duration * i

            # Format time to SRT format
            start_srt_time = format_time(start_time)
            end_srt_time = format_time(end_time)

            # Write the subtitle block
            srt_file.write(f"{i}\n")  # Subtitle number
            srt_file.write(f"{start_srt_time} --> {end_srt_time}\n")  # Subtitle time range
            srt_file.write(f"{line}\n")  # The subtitle text
            srt_file.write("\n")  # Blank line between subtitles


def merge_subtitle_command(video_file, subtitle_file, output_file):
    command = (
        f'ffmpeg -i "{video_file}" -vf "subtitles={subtitle_file}:charenc=UTF-8" '
        f'-c:v libx264 -crf 23 -c:a copy "{output_file}"'
    )

    # Run the command directly using os.system
    os.system(command)


trans = transcription(video_file)
translating = translate_text(trans)
create_srt(translating)
merge_subtitle_command(video_file, subtitle_file, output_file)
