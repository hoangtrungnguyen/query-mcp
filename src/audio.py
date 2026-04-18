"""Voice and audio conversation support"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

AUDIO_DIR = Path.home() / ".memory-mcp" / "audio"
AUDIO_DIR.mkdir(exist_ok=True, parents=True)


class AudioFormat(Enum):
    """Audio file formats"""
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    M4A = "m4a"


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    MANDARIN = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"


@dataclass
class AudioMetadata:
    """Metadata about audio file"""
    audio_id: str
    duration_seconds: float
    sample_rate: int
    channels: int
    format: AudioFormat
    language: Language
    confidence: float = 0.8
    noise_level: float = 0.0  # 0-1, higher = more noise
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize metadata"""
        return {
            "audio_id": self.audio_id,
            "duration_seconds": self.duration_seconds,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "format": self.format.value,
            "language": self.language.value,
            "confidence": self.confidence,
            "noise_level": self.noise_level,
            "created_at": self.created_at,
        }


@dataclass
class Transcription:
    """Speech-to-text result"""
    transcription_id: str
    audio_id: str
    text: str
    language: Language
    confidence: float
    word_timings: List[Dict] = field(default_factory=list)  # word + timestamp
    alternatives: List[str] = field(default_factory=list)  # Alternative interpretations
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize transcription"""
        return {
            "transcription_id": self.transcription_id,
            "audio_id": self.audio_id,
            "text": self.text,
            "language": self.language.value,
            "confidence": self.confidence,
            "word_count": len(self.text.split()),
            "alternatives": len(self.alternatives),
            "created_at": self.created_at,
        }


@dataclass
class SpeechSynthesis:
    """Text-to-speech result"""
    synthesis_id: str
    text: str
    language: Language
    voice: str  # Voice name/ID
    rate: float = 1.0  # Speech rate multiplier
    pitch: float = 1.0  # Pitch multiplier
    format: AudioFormat = AudioFormat.MP3
    duration_seconds: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Serialize synthesis"""
        return {
            "synthesis_id": self.synthesis_id,
            "text_length": len(self.text),
            "language": self.language.value,
            "voice": self.voice,
            "rate": self.rate,
            "pitch": self.pitch,
            "format": self.format.value,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at,
        }


@dataclass
class AudioSegment:
    """Segment of audio conversation"""
    segment_id: str
    conversation_id: str
    speaker_id: str
    speaker_name: str
    audio_id: str
    transcription_id: str
    text: str
    start_time: float
    end_time: float
    confidence: float
    emotion: Optional[str] = None  # Detected emotion
    tone: Optional[str] = None  # Tone/mood
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> Dict:
        """Serialize segment"""
        return {
            "segment_id": self.segment_id,
            "speaker_id": self.speaker_id,
            "speaker_name": self.speaker_name,
            "text": self.text,
            "duration_seconds": self.duration,
            "confidence": self.confidence,
            "emotion": self.emotion,
            "tone": self.tone,
            "created_at": self.created_at,
        }


class SpeechRecognitionEngine:
    """Handle speech-to-text"""

    def __init__(self):
        self.transcriptions: Dict[str, Transcription] = {}

    def transcribe_audio(
        self,
        audio_id: str,
        language: Language,
        audio_data: bytes,
    ) -> Transcription:
        """Transcribe audio to text"""
        # Simulated transcription
        transcription = Transcription(
            transcription_id=f"trans_{audio_id}",
            audio_id=audio_id,
            text="[Transcribed text would appear here]",
            language=language,
            confidence=0.92,
            word_timings=[],
            alternatives=[],
        )

        self.transcriptions[transcription.transcription_id] = transcription
        return transcription

    def detect_language(self, audio_data: bytes) -> Tuple[Language, float]:
        """Auto-detect language from audio"""
        # Simulated language detection
        return Language.ENGLISH, 0.95

    def get_confidence_score(self, transcription_id: str) -> float:
        """Get transcription confidence"""
        if transcription_id in self.transcriptions:
            return self.transcriptions[transcription_id].confidence
        return 0.0


class TextToSpeechEngine:
    """Handle text-to-speech"""

    AVAILABLE_VOICES = {
        Language.ENGLISH: ["en-US-Neural2-A", "en-US-Neural2-C", "en-GB-Neural2-A"],
        Language.SPANISH: ["es-ES-Neural2-A", "es-MX-Neural2-B"],
        Language.FRENCH: ["fr-FR-Neural2-A", "fr-CA-Neural2-B"],
        Language.GERMAN: ["de-DE-Neural2-A", "de-DE-Neural2-B"],
    }

    def __init__(self):
        self.syntheses: Dict[str, SpeechSynthesis] = {}

    def synthesize(
        self,
        text: str,
        language: Language,
        voice: Optional[str] = None,
        rate: float = 1.0,
    ) -> SpeechSynthesis:
        """Synthesize text to speech"""
        if not voice:
            voices = self.AVAILABLE_VOICES.get(language, [])
            voice = voices[0] if voices else "default"

        # Estimate duration (rough: ~1 second per 150 words)
        estimated_duration = max(0.5, len(text.split()) / 150)

        synthesis = SpeechSynthesis(
            synthesis_id=f"synth_{len(self.syntheses)}",
            text=text,
            language=language,
            voice=voice,
            rate=rate,
            duration_seconds=estimated_duration,
        )

        self.syntheses[synthesis.synthesis_id] = synthesis
        return synthesis

    def list_voices(self, language: Language) -> List[str]:
        """List available voices"""
        return self.AVAILABLE_VOICES.get(language, [])


class AudioConversationManager:
    """Manage audio conversations"""

    def __init__(self):
        self.stt_engine = SpeechRecognitionEngine()
        self.tts_engine = TextToSpeechEngine()
        self.audio_metadata: Dict[str, AudioMetadata] = {}
        self.segments: Dict[str, AudioSegment] = {}
        self.conversation_audio: Dict[str, List[str]] = {}  # conv_id -> segment_ids

    def process_audio_input(
        self,
        audio_id: str,
        audio_data: bytes,
        sample_rate: int,
        channels: int = 1,
    ) -> Tuple[AudioMetadata, Transcription]:
        """Process incoming audio"""
        # Detect language
        language, lang_confidence = self.stt_engine.detect_language(audio_data)

        # Create metadata
        duration = len(audio_data) / (sample_rate * channels * 2)  # 16-bit
        metadata = AudioMetadata(
            audio_id=audio_id,
            duration_seconds=duration,
            sample_rate=sample_rate,
            channels=channels,
            format=AudioFormat.WAV,
            language=language,
            confidence=lang_confidence,
        )

        self.audio_metadata[audio_id] = metadata

        # Transcribe
        transcription = self.stt_engine.transcribe_audio(audio_id, language, audio_data)

        return metadata, transcription

    def create_audio_segment(
        self,
        conversation_id: str,
        speaker_id: str,
        speaker_name: str,
        transcription_id: str,
        audio_id: str,
        text: str,
        start_time: float,
        end_time: float,
    ) -> AudioSegment:
        """Create audio segment in conversation"""
        segment = AudioSegment(
            segment_id=f"seg_{len(self.segments)}",
            conversation_id=conversation_id,
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            audio_id=audio_id,
            transcription_id=transcription_id,
            text=text,
            start_time=start_time,
            end_time=end_time,
            confidence=self.stt_engine.get_confidence_score(transcription_id),
        )

        self.segments[segment.segment_id] = segment

        if conversation_id not in self.conversation_audio:
            self.conversation_audio[conversation_id] = []
        self.conversation_audio[conversation_id].append(segment.segment_id)

        return segment

    def synthesize_response(
        self,
        text: str,
        language: Language,
        voice: Optional[str] = None,
    ) -> SpeechSynthesis:
        """Synthesize agent response to speech"""
        return self.tts_engine.synthesize(text, language, voice)

    def get_conversation_transcript(self, conversation_id: str) -> str:
        """Get full transcript of audio conversation"""
        segment_ids = self.conversation_audio.get(conversation_id, [])
        segments = [self.segments[sid] for sid in segment_ids if sid in self.segments]

        transcript = "\n".join([
            f"{s.speaker_name}: {s.text}"
            for s in sorted(segments, key=lambda x: x.start_time)
        ])

        return transcript

    def get_audio_analytics(self, conversation_id: str) -> Dict[str, Any]:
        """Get analytics for audio conversation"""
        segment_ids = self.conversation_audio.get(conversation_id, [])
        segments = [self.segments[sid] for sid in segment_ids if sid in self.segments]

        if not segments:
            return {}

        total_duration = sum(s.duration for s in segments)
        avg_confidence = sum(s.confidence for s in segments) / len(segments)

        speaker_stats = {}
        for segment in segments:
            if segment.speaker_id not in speaker_stats:
                speaker_stats[segment.speaker_id] = {
                    "name": segment.speaker_name,
                    "segments": 0,
                    "total_duration": 0.0,
                    "total_words": 0,
                }
            speaker_stats[segment.speaker_id]["segments"] += 1
            speaker_stats[segment.speaker_id]["total_duration"] += segment.duration
            speaker_stats[segment.speaker_id]["total_words"] += len(segment.text.split())

        return {
            "conversation_id": conversation_id,
            "segment_count": len(segments),
            "total_duration_seconds": total_duration,
            "avg_confidence": avg_confidence,
            "speaker_stats": speaker_stats,
        }


# Global manager
audio_manager = AudioConversationManager()


# MCP Tools (add to memory_server.py)

def process_audio_input(
    audio_id: str,
    audio_base64: str,
    sample_rate: int,
    language: str = None,
) -> dict:
    """Process audio input"""
    import base64
    audio_data = base64.b64decode(audio_base64)

    metadata, transcription = audio_manager.process_audio_input(
        audio_id,
        audio_data,
        sample_rate,
    )

    return {
        "audio_id": audio_id,
        "transcription": transcription.text,
        "language": transcription.language.value,
        "confidence": transcription.confidence,
    }


def synthesize_text_to_speech(
    text: str,
    language: str,
    voice: str = None,
) -> dict:
    """Synthesize text to speech"""
    synthesis = audio_manager.tts_engine.synthesize(
        text,
        Language(language),
        voice,
    )
    return synthesis.to_dict()


def create_audio_segment(
    conversation_id: str,
    speaker_id: str,
    speaker_name: str,
    transcription_id: str,
    audio_id: str,
    text: str,
    start_time: float,
    end_time: float,
) -> dict:
    """Create audio segment"""
    segment = audio_manager.create_audio_segment(
        conversation_id,
        speaker_id,
        speaker_name,
        transcription_id,
        audio_id,
        text,
        start_time,
        end_time,
    )
    return segment.to_dict()


def get_conversation_transcript(conversation_id: str) -> dict:
    """Get full transcript"""
    transcript = audio_manager.get_conversation_transcript(conversation_id)
    return {"conversation_id": conversation_id, "transcript": transcript}


def get_audio_conversation_analytics(conversation_id: str) -> dict:
    """Get audio analytics"""
    return audio_manager.get_audio_analytics(conversation_id)


if __name__ == "__main__":
    # Test audio
    manager = AudioConversationManager()

    # Process audio
    audio_data = b"fake audio data"
    metadata, trans = manager.process_audio_input("audio_1", audio_data, 16000)
    print(f"Transcribed: {trans.text}")

    # Create segment
    segment = manager.create_audio_segment(
        "conv_1",
        "user_1",
        "Alice",
        trans.transcription_id,
        "audio_1",
        trans.text,
        0.0,
        5.0,
    )
    print(f"Segment: {segment.segment_id}")

    # Synthesize response
    synthesis = manager.tts_engine.synthesize(
        "This is the agent response",
        Language.ENGLISH,
    )
    print(f"Synthesis: {synthesis.synthesis_id}")

    # Analytics
    analytics = manager.get_audio_analytics("conv_1")
    print(f"Analytics: {json.dumps(analytics, indent=2)}")
