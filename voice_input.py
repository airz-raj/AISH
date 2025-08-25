# voice_input.py
"""
Voice input module for AISH with multiple fallback options
"""

import os
import sys
import threading
import time
import select
from typing import Optional, Callable

# Try to import speech recognition libraries with graceful fallbacks
try:
    import speech_recognition as sr
    HAS_SPEECH_RECOGNITION = True
except ImportError:
    HAS_SPEECH_RECOGNITION = False

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

class VoiceInput:
    """Voice input handler with multiple fallback strategies"""
    
    def __init__(self):
        self.recognizer = None
        self.microphone = None
        self.is_listening = False
        self.last_result = None
        self.setup_recognizer()
    
    def setup_recognizer(self):
        """Setup speech recognition with available backends"""
        if not HAS_SPEECH_RECOGNITION:
            return False
        
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300  # Adjust for sensitivity
            self.recognizer.pause_threshold = 0.8   # Time to wait after speech
            self.recognizer.dynamic_energy_threshold = True
            
            # Try to setup microphone
            try:
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                return True
            except Exception:
                # Microphone not available, but recognizer still works for file input
                return True
                
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """Check if voice input is available"""
        return self.recognizer is not None and self.microphone is not None
    
    def get_voice_status(self) -> str:
        """Get voice input status message"""
        if not HAS_SPEECH_RECOGNITION:
            return "Voice input disabled (install: pip install SpeechRecognition)"
        elif not self.is_available():
            return "Voice input unavailable (microphone not detected)"
        else:
            return "Voice input ready 🎤"
    
    def listen_voice(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice input with timeout"""
        if not self.recognizer or not self.microphone:
            return None
        
        try:
            print("🎤 Listening... (speak now)")
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=4)
            
            print("🔍 Processing...")
            text = self.recognizer.recognize_google(audio)
            return text.lower().strip()
            
        except sr.WaitTimeoutError:
            print("⏰ Listening timeout")
            return None
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return None
        except sr.RequestError as e:
            print(f"🌐 Network error: {e}")
            return None
        except Exception as e:
            print(f"❌ Voice error: {e}")
            return None
    
    def voice_to_command(self, prompt: str = "Speak your command") -> Optional[str]:
        """Convert voice to command with visual feedback"""
        if not self.is_available():
            return None
        
        print(f"\n🎤 {prompt} (say 'cancel' to stop)")
        print("   Press Enter to use keyboard instead")
        
        # Clear any previous result
        self.last_result = None
        self.is_listening = True
        
        # Start listening in background
        voice_thread = threading.Thread(target=self._listen_background)
        voice_thread.daemon = True
        voice_thread.start()
        
        # Give the voice thread a moment to start
        time.sleep(0.5)
        
        # Show listening animation for a limited time
        listen_timeout = 10
        start_time = time.time()
        
        while time.time() - start_time < listen_timeout and self.is_listening:
            if self.last_result is not None:
                # Voice input captured successfully - return it immediately
                self.is_listening = False
                return self.last_result
            
            # Check for keyboard input without blocking
            try:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    keyboard_input = sys.stdin.readline().strip()
                    if keyboard_input:
                        self.is_listening = False
                        return keyboard_input
            except:
                pass
            
            time.sleep(0.1)
        
        # Timeout or listening stopped
        self.is_listening = False
        
        # Check one last time if we got a result right at the end
        if self.last_result is not None:
            return self.last_result
        
        return None
    
    def _listen_background(self):
        """Background listening thread"""
        try:
            result = self.listen_voice(timeout=8)
            if result and result.lower() != "cancel":
                print(f"🗣️  Heard: {result}")
                self.last_result = result
            else:
                # Clear result if it's cancel or None
                self.last_result = None
        except Exception as e:
            print(f"❌ Voice error: {e}")
            self.last_result = None
        finally:
            self.is_listening = False

# Global voice input instance
voice_handler = VoiceInput()

def setup_voice_input():
    """Initialize voice input"""
    return voice_handler

def get_voice_input(prompt: str = "Speak your command") -> Optional[str]:
    """Get voice input with fallback to keyboard"""
    result = voice_handler.voice_to_command(prompt)
    # Add a small delay to ensure the voice thread is cleaned up
    time.sleep(0.1)
    return result

def is_voice_available() -> bool:
    """Check if voice input is available"""
    return voice_handler.is_available()

def voice_status() -> str:
    """Get voice status message"""
    return voice_handler.get_voice_status()

# Alternative: System voice input (macOS/Windows)
def system_voice_input() -> Optional[str]:
    """Use system voice input if available"""
    try:
        if sys.platform == "darwin":  # macOS
            # Use AppleScript for voice input
            import subprocess
            result = subprocess.run([
                'osascript', '-e',
                'display dialog "Speak your command" with title "AISH Voice Input" default answer ""'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Extract text from AppleScript response
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'text returned:' in line:
                        return line.split('text returned:')[1].strip().strip('"')
        
        elif sys.platform == "win32":  # Windows
            # Use Windows Speech Recognition (simplified)
            print("Windows voice input: Say your command to Cortana/Windows Speech Recognition")
            time.sleep(2)
            # Would need more complex integration for Windows
            
    except Exception:
        pass
    
    return None

# Voice command mappings (for reference - this is used in aish.py now)
VOICE_COMMAND_MAP = {
    "run": "1",
    "execute": "1",
    "command": "1",
    "browse": "2",
    "list": "2",
    "commands": "2",
    "history": "3",
    "log": "3",
    "utilities": "4",
    "tools": "4",
    "built-in": "4",
    "safety": "5",
    "check": "5",
    "secure": "5",
    "help": "6",
    "tips": "6",
    "exit": "7",
    "quit": "7",
    "stop": "7",
    "cancel": "cancel",
}