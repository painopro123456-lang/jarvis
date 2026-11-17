"""Optional speech output and microphone input."""
from __future__ import annotations

import threading


class Voice:
    def __init__(self):
        self._engine = None
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 180)
        except Exception:
            self._engine = None

    def speak(self, text: str) -> None:
        if self._engine is None:
            return
        def run():
            try:
                self._engine.say(text)
                self._engine.runAndWait()
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()

    def listen_once(self, timeout: int = 5, phrase_time_limit: int = 8) -> str:
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.4)
                audio = recognizer.listen(source, timeout=timeout,
                                          phrase_time_limit=phrase_time_limit)
            return recognizer.recognize_google(audio)
        except ImportError as exc:
            raise RuntimeError("Microphone support is optional. Install requirements-voice.txt and a working PyAudio build.") from exc
        except Exception as exc:
            raise RuntimeError(f"Voice input unavailable: {exc}") from exc
