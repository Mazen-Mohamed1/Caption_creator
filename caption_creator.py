import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import zipfile
import speech_recognition as sr
from moviepy.editor import VideoFileClip
from googletrans import Translator
import threading
import tempfile

# Initialize the customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class SubtitleApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window settings
        self.title("Subtitle Generator")
        self.geometry("500x400")

        # Label
        self.label = ctk.CTkLabel(self, text="Choose an option to generate subtitles", font=("Arial", 16))
        self.label.pack(pady=20)

        # Buttons for choosing action
        self.single_video_btn = ctk.CTkButton(self, text="Process Single Video", command=self.process_single_video)
        self.single_video_btn.pack(pady=10)

        self.folder_btn = ctk.CTkButton(self, text="Process Folder of Videos", command=self.process_folder)
        self.folder_btn.pack(pady=10)

        self.zip_btn = ctk.CTkButton(self, text="Process Zip of Videos", command=self.process_zip)
        self.zip_btn.pack(pady=10)

        # Progress bar for indicating process
        self.progress_bar = ctk.CTkProgressBar(self, width=400)
        self.progress_bar.pack(pady=20)

        # Output label for status updates
        self.output_label = ctk.CTkLabel(self, text="", font=("Arial", 12))
        self.output_label.pack(pady=20)

    def update_status(self, text):
        if self.output_label.winfo_exists():  # Check if the widget still exists
            self.output_label.configure(text=text)

    def set_progress_bar(self, value):
        if self.progress_bar.winfo_exists():  # Check if the widget still exists
            self.progress_bar.set(value)

    def transcription(self, video_path):
        # Create a temporary file for storing audio
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio_file:
            audio_file_path = temp_audio_file.name

        try:
            # Load the video and extract the audio
            video_clip = VideoFileClip(video_path)
            audio_clip = video_clip.audio
            audio_clip.write_audiofile(audio_file_path, codec='pcm_s16le')

            # Close video and audio clips
            audio_clip.close()
            video_clip.close()

            # Transcribe the audio using Google Speech Recognition
            recognizer = sr.Recognizer()
            with sr.AudioFile(audio_file_path) as source:
                audio_data = recognizer.record(source)
                transcript = recognizer.recognize_google(audio_data)
        finally:
            os.remove(audio_file_path)  # Delete the temporary audio file

        return transcript

    def translate_text(self, text, target_language='ar'):
        translator = Translator()
        try:
            result = translator.translate(text, dest=target_language)
            return result.text
        except Exception as e:
            self.update_status(f"Translation error: {str(e)}")
            return ""

    def create_srt(self, translated_text, video_duration, output_srt_file, chunk_size=100):
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

        subtitle_duration = video_duration / len(lines)

        def format_time(seconds):
            milliseconds = int((seconds % 1) * 1000)
            seconds = int(seconds)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

        with open(output_srt_file, "w", encoding="utf-8") as srt_file:
            for i, line in enumerate(lines, 1):
                start_time = subtitle_duration * (i - 1)
                end_time = subtitle_duration * i

                start_srt_time = format_time(start_time)
                end_srt_time = format_time(end_time)

                srt_file.write(f"{i}\n")
                srt_file.write(f"{start_srt_time} --> {end_srt_time}\n")
                srt_file.write(f"{line}\n")
                srt_file.write("\n")

    def process_video(self, video_file, output_folder):
        self.update_status(f"Processing video: {video_file}")
        self.progress_bar.set(0.3)

        subtitle_file = os.path.join(output_folder, os.path.basename(video_file).replace('.mp4', '.srt'))

        # Generate and translate subtitles
        transcript = self.transcription(video_file)
        translated_text = self.translate_text(transcript)
        self.progress_bar.set(0.6)

        # Use the video duration for SRT timing
        video_clip = VideoFileClip(video_file)
        self.create_srt(translated_text, video_clip.duration, subtitle_file)

        # Ensure the video clip is closed
        video_clip.close()

        # Remove any video files from the output folder if needed
        video_base_name = os.path.basename(video_file)
        video_output_path = os.path.join(output_folder, video_base_name)
        if os.path.exists(video_output_path):
            os.remove(video_output_path)  # Remove the video if it exists

        self.progress_bar.set(1.0)

    def process_videos_in_folder(self, folder_path, output_folder):
        video_files = [f for f in os.listdir(folder_path) if f.endswith('.mp4')]
        total_videos = len(video_files)
        for i, file_name in enumerate(video_files, 1):
            video_file_path = os.path.join(folder_path, file_name)
            self.process_video(video_file_path, output_folder)
            self.progress_bar.set((i / total_videos) * 0.9)  # Update progress bar

        self.progress_bar.set(1.0)  # Set progress to complete
        self.success_message()  # Show success message after processing

    def extract_zip(self, zip_path, extract_to):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        self.update_status(f"Extracted '{zip_path}'")

    def process_videos_in_zip(self, zip_file_path):
        base_name = os.path.splitext(os.path.basename(zip_file_path))[0]
        caption_folder_path = os.path.join(os.path.dirname(zip_file_path), 'captions_' + base_name)

        if not os.path.exists(caption_folder_path):
            os.makedirs(caption_folder_path)

        self.extract_zip(zip_file_path, caption_folder_path)
        self.process_videos_in_folder(caption_folder_path, caption_folder_path)

    def process_single_video(self):
        video_file = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if video_file:
            video_base_name = os.path.splitext(os.path.basename(video_file))[0]
            caption_folder = os.path.join(os.path.dirname(video_file), 'captions_' + video_base_name)

            if not os.path.exists(caption_folder):
                os.makedirs(caption_folder)

            threading.Thread(target=self.process_video, args=(video_file, caption_folder), daemon=True).start()

    def process_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            folder_base_name = os.path.basename(folder_path)
            caption_folder = os.path.join(os.path.dirname(folder_path), 'captions_' + folder_base_name)

            if not os.path.exists(caption_folder):
                os.makedirs(caption_folder)

            threading.Thread(target=self.process_videos_in_folder, args=(folder_path, caption_folder), daemon=True).start()

    def process_zip(self):
        zip_file_path = filedialog.askopenfilename(filetypes=[("Zip files", "*.zip")])
        if zip_file_path:
            threading.Thread(target=self.process_videos_in_zip, args=(zip_file_path,), daemon=True).start()

    def success_message(self):
        messagebox.showinfo("Success", "All files created successfully!")
        # Delay destruction or only destroy after confirming all threads/processes are done
        self.after(500, self.destroy)  # Destroy after a delay


if __name__ == "__main__":
    app = SubtitleApp()
    app.mainloop()
