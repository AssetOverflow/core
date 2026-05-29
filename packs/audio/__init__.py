"""packs.audio — audio modality packs (ADR-0181). See loader.load_audio_pack."""

from packs.audio.loader import AudioPackError, LoadedAudioPack, load_audio_pack

__all__ = ["load_audio_pack", "LoadedAudioPack", "AudioPackError"]
