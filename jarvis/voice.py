"""Optional speech output, microphone input and opt-in wake-word listening."""
from __future__ import annotations
import threading

class Voice:
    def __init__(self):
        self._engine=None
        self._wake_stop=None
        self._lock=threading.Lock()
        try:
            import pyttsx3
            self._engine=pyttsx3.init()
            self._engine.setProperty("rate",180)
        except Exception: self._engine=None

    def speak(self,text: str, personality: str="calm"):
        if self._engine is None: return
        rates={"calm":165,"standard":180,"energetic":200}
        def run():
            try:
                with self._lock:
                    self._engine.setProperty("rate",rates.get(personality,180))
                    self._engine.say(text)
                    self._engine.runAndWait()
            except Exception: pass
        threading.Thread(target=run,daemon=True).start()

    def stop_speaking(self):
        if self._engine is not None:
            try: self._engine.stop()
            except Exception: pass

    def listen_once(self,timeout: int=5,phrase_time_limit: int=8) -> str:
        try:
            import speech_recognition as sr
            recognizer=sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source,duration=0.4)
                audio=recognizer.listen(source,timeout=timeout,phrase_time_limit=phrase_time_limit)
            return recognizer.recognize_google(audio)
        except ImportError as exc:
            raise RuntimeError("Microphone support is optional. Install requirements-voice.txt and a working PyAudio build.") from exc
        except Exception as exc: raise RuntimeError(f"Voice input unavailable: {exc}") from exc

    def start_wake_word(self, callback, wake_word: str="jarvis"):
        """Opt-in continuous listener. Speech recognition is sent to Google's service."""
        try:
            import speech_recognition as sr
            recognizer=sr.Recognizer()
            microphone=sr.Microphone()
            def heard(rec, audio):
                try:
                    phrase=rec.recognize_google(audio)
                    lower=phrase.lower()
                    if wake_word in lower:
                        command=lower.split(wake_word,1)[1].strip(" ,.!?")
                        callback(command or "I'm listening.")
                except Exception: pass
            self._wake_stop=recognizer.listen_in_background(microphone,heard,phrase_time_limit=6)
            return "Wake-word listening enabled. Speech recognition uses Google's online service."
        except Exception as exc:
            raise RuntimeError(f"Wake-word listening unavailable: {exc}") from exc

    def stop_wake_word(self):
        if self._wake_stop:
            try: self._wake_stop(wait_for_stop=False)
            except Exception: pass
            self._wake_stop=None
            return "Wake-word listening stopped."
        return "Wake-word listening is already stopped."
