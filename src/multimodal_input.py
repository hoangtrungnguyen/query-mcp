"""Multi-modal input processing and fusion"""

import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

MULTIMODAL_DIR = Path.home() / ".memory-mcp" / "multimodal-input"
MULTIMODAL_DIR.mkdir(exist_ok=True, parents=True)


class InputModality(Enum):
    """Input modalities"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    STRUCTURED = "structured"  # JSON, tables, etc.
    MIXED = "mixed"


class ContentType(Enum):
    """Content types extracted"""
    TEXT_CONTENT = "text_content"
    VISUAL_DESCRIPTION = "visual_description"
    AUDIO_TRANSCRIPT = "audio_transcript"
    STRUCTURED_DATA = "structured_data"
    METADATA = "metadata"


@dataclass
class ExtractedContent:
    """Content extracted from modality"""
    content_type: ContentType
    text: str
    confidence: float
    source_modality: InputModality
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serialize content"""
        return {
            "type": self.content_type.value,
            "modality": self.source_modality.value,
            "confidence": round(self.confidence, 2),
            "length": len(self.text.split()),
        }


@dataclass
class ImageInput:
    """Image input with extraction"""
    image_id: str
    image_path: str
    description: str  # Visual description
    objects_detected: List[str] = field(default_factory=list)
    text_in_image: str = ""
    confidence: float = 0.8

    def to_dict(self) -> Dict:
        """Serialize image input"""
        return {
            "image_id": self.image_id,
            "objects": len(self.objects_detected),
            "confidence": round(self.confidence, 2),
        }


@dataclass
class AudioInput:
    """Audio input with transcription"""
    audio_id: str
    audio_path: str
    transcript: str
    duration: float  # Seconds
    language: str = "en"
    confidence: float = 0.85
    speaker_segments: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize audio input"""
        return {
            "audio_id": self.audio_id,
            "duration": round(self.duration, 1),
            "language": self.language,
            "confidence": round(self.confidence, 2),
        }


@dataclass
class StructuredInput:
    """Structured data input"""
    data_id: str
    data_format: str  # JSON, CSV, TABLE, etc.
    content: Dict[str, Any]
    schema: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""

    def to_dict(self) -> Dict:
        """Serialize structured input"""
        return {
            "data_id": self.data_id,
            "format": self.data_format,
            "keys": len(self.content),
        }


@dataclass
class UnifiedInputRepresentation:
    """Unified representation across modalities"""
    representation_id: str
    primary_modality: InputModality
    extracted_text: str  # Main text content
    visual_context: str = ""  # From images
    audio_context: str = ""  # From audio
    structured_context: Dict[str, Any] = field(default_factory=dict)  # From structured
    combined_query: str = ""  # Synthesized query
    modalities_present: List[InputModality] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize representation"""
        return {
            "representation_id": self.representation_id,
            "primary": self.primary_modality.value,
            "modalities": [m.value for m in self.modalities_present],
            "combined_query_length": len(self.combined_query.split()),
        }


class InputExtractor:
    """Extract content from modalities"""

    @staticmethod
    def extract_from_text(text: str) -> ExtractedContent:
        """Extract from text input"""
        return ExtractedContent(
            content_type=ContentType.TEXT_CONTENT,
            text=text,
            confidence=1.0,
            source_modality=InputModality.TEXT,
        )

    @staticmethod
    def extract_from_image(
        image_path: str,
        image_id: str,
    ) -> ImageInput:
        """Extract from image input"""
        # Placeholder: in real system would use vision API
        description = f"Image at {image_path}"
        objects = ["object_1", "object_2"]

        return ImageInput(
            image_id=image_id,
            image_path=image_path,
            description=description,
            objects_detected=objects,
            confidence=0.8,
        )

    @staticmethod
    def extract_from_audio(
        audio_path: str,
        audio_id: str,
    ) -> AudioInput:
        """Extract from audio input"""
        # Placeholder: in real system would use speech-to-text API
        transcript = f"Transcription of {audio_path}"

        return AudioInput(
            audio_id=audio_id,
            audio_path=audio_path,
            transcript=transcript,
            duration=60.0,
            confidence=0.85,
        )

    @staticmethod
    def extract_from_structured(
        data: Dict[str, Any],
        data_id: str,
        data_format: str = "JSON",
    ) -> StructuredInput:
        """Extract from structured data"""
        summary = f"Contains {len(data)} keys"

        return StructuredInput(
            data_id=data_id,
            data_format=data_format,
            content=data,
            summary=summary,
        )


class InputFuser:
    """Fuse multi-modal inputs into unified representation"""

    @staticmethod
    def fuse_inputs(
        text_input: Optional[str],
        image_inputs: List[ImageInput],
        audio_inputs: List[AudioInput],
        structured_inputs: List[StructuredInput],
    ) -> UnifiedInputRepresentation:
        """Fuse inputs into unified representation"""
        modalities = []
        extracted_text = text_input or ""

        if text_input:
            modalities.append(InputModality.TEXT)

        visual_context = ""
        if image_inputs:
            modalities.append(InputModality.IMAGE)
            visual_context = "; ".join([img.description for img in image_inputs])

        audio_context = ""
        if audio_inputs:
            modalities.append(InputModality.AUDIO)
            audio_context = "; ".join([aud.transcript for aud in audio_inputs])

        structured_context = {}
        if structured_inputs:
            modalities.append(InputModality.STRUCTURED)
            for struct in structured_inputs:
                structured_context.update(struct.content)

        # Synthesize combined query
        parts = []
        if extracted_text:
            parts.append(f"Text: {extracted_text}")
        if visual_context:
            parts.append(f"Visual: {visual_context[:100]}")
        if audio_context:
            parts.append(f"Audio: {audio_context[:100]}")
        if structured_context:
            parts.append(f"Data: {len(structured_context)} fields")

        combined_query = "; ".join(parts)

        primary_modality = (
            InputModality.TEXT if text_input else
            InputModality.IMAGE if image_inputs else
            InputModality.AUDIO if audio_inputs else
            InputModality.STRUCTURED
        )

        return UnifiedInputRepresentation(
            representation_id=f"unified_{int(datetime.now().timestamp())}",
            primary_modality=primary_modality,
            extracted_text=extracted_text,
            visual_context=visual_context,
            audio_context=audio_context,
            structured_context=structured_context,
            combined_query=combined_query,
            modalities_present=modalities,
        )


class MultimodalProcessor:
    """Process multi-modal inputs"""

    def __init__(self):
        self.processed_inputs: Dict[str, UnifiedInputRepresentation] = {}

    def process_input(
        self,
        text: Optional[str] = None,
        image_paths: List[str] = None,
        audio_paths: List[str] = None,
        structured_data: List[Dict] = None,
    ) -> Dict[str, Any]:
        """Process multi-modal input"""
        # Extract from each modality
        text_content = None
        if text:
            text_content = InputExtractor.extract_from_text(text).text

        images = []
        if image_paths:
            for i, path in enumerate(image_paths):
                img = InputExtractor.extract_from_image(path, f"img_{i}")
                images.append(img)

        audio = []
        if audio_paths:
            for i, path in enumerate(audio_paths):
                aud = InputExtractor.extract_from_audio(path, f"aud_{i}")
                audio.append(aud)

        structured = []
        if structured_data:
            for i, data in enumerate(structured_data):
                struct = InputExtractor.extract_from_structured(data, f"struct_{i}")
                structured.append(struct)

        # Fuse into unified representation
        unified = InputFuser.fuse_inputs(text_content, images, audio, structured)
        self.processed_inputs[unified.representation_id] = unified

        return {
            "representation_id": unified.representation_id,
            "primary_modality": unified.primary_modality.value,
            "modalities_fused": [m.value for m in unified.modalities_present],
            "combined_query_length": len(unified.combined_query.split()),
            "has_visual": bool(images),
            "has_audio": bool(audio),
            "has_structured": bool(structured),
        }

    def get_unified_query(self, representation_id: str) -> Optional[str]:
        """Get unified query from representation"""
        rep = self.processed_inputs.get(representation_id)
        return rep.combined_query if rep else None


class MultimodalManager:
    """Manage multi-modal processing"""

    def __init__(self):
        self.processors: Dict[str, MultimodalProcessor] = {}

    def create_processor(self, processor_id: str) -> MultimodalProcessor:
        """Create processor"""
        processor = MultimodalProcessor()
        self.processors[processor_id] = processor
        return processor

    def get_processor(self, processor_id: str) -> Optional[MultimodalProcessor]:
        """Get processor"""
        return self.processors.get(processor_id)


# Global manager
multimodal_manager = MultimodalManager()


# MCP Tools

def create_multimodal_processor(processor_id: str) -> dict:
    """Create multimodal processor"""
    processor = multimodal_manager.create_processor(processor_id)
    return {"processor_id": processor_id, "created": True}


def process_multimodal_input(
    processor_id: str,
    text: str = None,
    image_paths: list = None,
    audio_paths: list = None,
    structured_data: list = None,
) -> dict:
    """Process multimodal input"""
    processor = multimodal_manager.get_processor(processor_id)
    if not processor:
        return {"error": "Processor not found"}

    return processor.process_input(text, image_paths, audio_paths, structured_data)


def get_unified_query(processor_id: str, representation_id: str) -> dict:
    """Get unified query"""
    processor = multimodal_manager.get_processor(processor_id)
    if not processor:
        return {"error": "Processor not found"}

    query = processor.get_unified_query(representation_id)
    return {"query": query} if query else {"error": "Representation not found"}


if __name__ == "__main__":
    processor = MultimodalProcessor()

    result = processor.process_input(
        text="What's in this image and audio?",
        image_paths=["/path/to/image.jpg"],
        audio_paths=["/path/to/audio.wav"],
    )

    print(f"Result: {json.dumps(result, indent=2)}")
