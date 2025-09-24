# PARA EL HEMISH DE FUTURO!!!
#Recuerda que esto es solo una prubea del chatbot para probar su funcionamiento 
import os
import sys
import json
import queue
import signal
import requests
import pyttsx3
import sounddevice as sd
from vosk import Model, KaldiRecognizer

SAMPLE_RATE = 16000
BLOCKSIZE = 8000  


def pick_spanish_voice(engine: pyttsx3.Engine):
    
    try:
        for v in engine.getProperty('voices'):
            name = (v.name or "").lower()
            lang = ",".join(v.languages) if isinstance(v.languages, (list, tuple)) else str(v.languages)
            lang = (lang or "").lower()
            if "es" in lang or "spanish" in name or "es_" in name:
                engine.setProperty('voice', v.id)
                break
    except Exception:
        pass

def tts_say(text: str):
    engine = pyttsx3.init()
    pick_spanish_voice(engine)
    engine.setProperty('rate', 175)  
    engine.setProperty('volume', 1.0)
    engine.say(text)
    engine.runAndWait()


def brain_rules(user_text: str) -> str:
    
    t = user_text.lower().strip()
    if not t:
        return "No te escuché bien, ¿puedes repetir por favor?"
    if any(k in t for k in ["hola", "buenas", "qué tal", "que tal"]):
        return "¡Hola! Soy tu asistente por voz. ¿En qué te puedo ayudar?"
    if "tu nombre" in t or "cómo te llamas" in t:
        return "Puedes llamarme Asistente por Voz."
    if "hora" in t:
        import datetime
        now = datetime.datetime.now().strftime("%H:%M")
        return f"Son las {now}."
    if "salir" in t or "terminar" in t or "adiós" in t or "adios" in t:
        return "__EXIT__"
    
    return f"Me dijiste: {user_text}"

def brain_ollama(user_text: str) -> str:
    
    try:
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": os.getenv("OLLAMA_MODEL", "qwen3:8b"),
            "messages": [
                {"role": "system", "content": "Eres un asistente útil que habla español de manera clara y breve."},
                {"role": "user", "content": user_text},
            ],
            "stream": False
        }
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        
        return data.get("message", {}).get("content", "").strip() or "Lo siento, no tengo respuesta."
    except Exception as e:
        return f"No pude consultar el modelo local de Ollama ({e})."

def generate_reply(user_text: str) -> str:
    if os.getenv("OLLAMA", "0") == "1":
        return brain_ollama(user_text)
    return brain_rules(user_text)


class MicRecognizer:
    def __init__(self, model_path: str, sample_rate: int = SAMPLE_RATE):
        if not os.path.isdir(model_path):
            raise RuntimeError(
                f"No se encontró el modelo Vosk en: {model_path}\n"
                "Descárgalo y descomprímelo. Consulta el README.md."
            )
        self.model = Model(model_path)
        self.rec = KaldiRecognizer(self.model, sample_rate)
        self.rec.SetWords(True)
        self.q = queue.Queue()

    def audio_callback(self, indata, frames, time, status):
        if status:
            
            print(f"[AUDIO] {status}", file=sys.stderr)
        
        self.q.put(bytes(indata))

    def listen_and_transcribe(self) -> str:
        
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            dtype="int16",
            channels=1,
            callback=self.audio_callback,
        ):
            while True:
                data = self.q.get()
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = (res.get("text") or "").strip()
                    if text:
                        return text
                    else:
                        
                        continue
                

def main():
    print("="*60)
    print(" Chatbot por micrófono (Vosk + pyttsx3, opcional Ollama) ")
    print("="*60)
    model_path = os.getenv("VOSK_MODEL", "models/vosk-model-small-es")
    print(f"Usando modelo Vosk en: {model_path}")
    print("Comandos de voz útiles: 'salir', 'terminar', 'adiós'.\n")

    recognizer = MicRecognizer(model_path)

    # La cosa esta se cierra con Ctrl+C
    def handle_sigint(sig, frame):
        print("\nSaliendo...")
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        print("\n Habla ahora... (Ctrl+C para salir)")
        try:
            user_text = recognizer.listen_and_transcribe()
        except Exception as e:
            print(f"[Error grabando/transcribiendo]: {e}")
            break

        print(f"Tú: {user_text}")
        reply = generate_reply(user_text)

        if reply == "__EXIT__":
            tts_say("Hasta luego. ¡Adiós!")
            print("Bot: Adiós ")
            break

        print(f"Bot: {reply}")
        try:
            tts_say(reply)
        except Exception as e:
            print(f"[Error TTS]: {e}")

if __name__ == "__main__":
    main()

