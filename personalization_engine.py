"""
1. Take user audio recordings
2. Learn their unique speaking patterns
3. Create a "voice profile" that captures their style
4. Use this profile to make Piper TTS sound like them
"""

import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import numpy as np

from audio_preprocessor import AudioPreprocessor
from feature_extractor import FeatureExtractor

logger = logging.getLogger(__name__)


class VoiceProfile:
        
    def __init__(self, user_id: str, user_name: str = "Unknown"):
        self.user_id = user_id
        self.user_name = user_name
        self.created_date = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()
        
        # Speaking pattern features
        self.speaking_rate_wpm = None
        self.average_pause_duration = None
        self.mean_pitch = None
        self.pitch_range = None
        self.emotion_profile = {}
        
        # Raw data
        self.energy_levels = None
        self.pitch_contour = None
        
        logger.info(f"VoiceProfile created for user: {user_id} ({user_name})")
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'user_name': self.user_name,
            'created_date': self.created_date,
            'last_updated': self.last_updated,
            'speaking_characteristics': {
                'speaking_rate_wpm': self.speaking_rate_wpm,
                'average_pause_duration': self.average_pause_duration,
                'mean_pitch': self.mean_pitch,
                'pitch_range': self.pitch_range,
            },
            'emotion_profile': self.emotion_profile,
        }
    
    def save_json(self, filepath):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Profile saved to {filepath}")
    
    def save_yaml(self, filepath):
        with open(filepath, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
        logger.info(f"Profile saved to {filepath}")


class PersonalizationEngine:    
    
    def __init__(self, sr=22050):

        self.sr = sr
        self.preprocessor = AudioPreprocessor(sr=sr)
        self.feature_extractor = FeatureExtractor(sr=sr)
        self.voice_profiles = {}
        
        logger.info("PersonalizationEngine initialized")
    
    # def load_audio_file(self, audio_path):
        
    #     logger.info(f"Loading audio file: {audio_path}")
        
    #     # Load and preprocess
    #     audio, sr = self.preprocessor.preprocess(audio_path)
        
    #     logger.info(f"Audio loaded: {len(audio)} samples, {sr} Hz sample rate")
        
    #     return audio
    
    # def analyze_user_audio(self, audio):        
    #     logger.info("Analyzing user audio patterns")
        
    #     patterns = self.feature_extractor.extract_all_features(audio)
        
    #     if patterns is None:
    #         logger.error("Failed to extract patterns from audio")
    #         return None
        
    #     logger.info("User audio analysis complete")
        
    #     return patterns
    
    def create_voice_profile(self, user_id, user_name, audio_path):
        
        logger.info(f"Creating voice profile for {user_name} ({user_id})")
        
        try:
            # Step 1: Load and preprocess audio
            audio,sr = self.preprocessor.preprocess(audio_path)
            logger.info("Step 1: Audio loaded and cleaned")
            
            # Step 2: Analyze audio to extract patterns
            patterns = self.feature_extractor.extract_all_features(audio)
            if patterns is None:
                return None
            logger.info("Step 2: Patterns analyzed")
            
            # Step 3: Create profile object
            profile = VoiceProfile(user_id=user_id, user_name=user_name)
            
            # Step 4: Fill profile with extracted data
            profile.speaking_rate_wpm = patterns.speaking_rate_wpm
            profile.average_pause_duration = patterns.average_pause_duration
            profile.mean_pitch = patterns.mean_pitch
            profile.pitch_range = patterns.pitch_range
            profile.energy_levels = patterns.energy_levels
            profile.pitch_contour = patterns.pitch_contour
            profile.emotion_profile = self._infer_emotion(profile)
            logger.info("Step 3: Profile created")
            
            # Store profile for later use
            self.voice_profiles[user_id] = profile
            
            logger.info(f"Voice profile for {user_name} created successfully!")
            
            return profile
        
        except Exception as e:
            logger.error(f"Error creating voice profile: {str(e)}")
            raise
    
    def get_synthesis_parameters(self, user_id) -> Dict[str, Any]:
        
        # Get parameters to pass to Piper TTS for personalized synthesis
        if user_id not in self.voice_profiles:
            logger.error(f"No profile found for user {user_id}")
            return None
        
        profile = self.voice_profiles[user_id]
        
        # Create parameter set that Piper TTS can use
        params = {
            'pitch_adjust': self._normalize_pitch_for_synthesis(
                profile.mean_pitch
            ),
            'speaking_rate_adjust': self._normalize_speed_for_synthesis(
                profile.speaking_rate_wpm
            ),
            'pause_duration': profile.average_pause_duration,
            'energy_level': np.mean(profile.energy_levels) if profile.energy_levels else 0.5,
        }
        
        logger.info(f"Synthesis parameters generated for user {user_id}")
        logger.info(f"  Pitch adjust: {params['pitch_adjust']:.2f}")
        logger.info(f"  Speed adjust: {params['speaking_rate_adjust']:.2f}")
        logger.info(f"  Pause duration: {params['pause_duration']:.3f}s")
        
        return params
    
    def _normalize_pitch_for_synthesis(self, mean_pitch):
        
        #Convert measured pitch (Hz) to Piper parameter (0.5 - 2.0)        
        if mean_pitch is None:
            return 1.0  # Default (neutral)
        
        # Normalize to 0.5-2.0 range
        normalized = np.clip((mean_pitch / 150), 0.5, 2.0)        
        return normalized
    
    def _normalize_speed_for_synthesis(self, wpm):
        """
        Convert speaking rate (WPM) to Piper parameter
        Convert words-per-minute into a factor that Piper understands (0.5 - 2.0).
        
        Normal speed ~ 150 WPM → adjustment = 1.0
        Fast ~ 180 WPM → adjustment = 1.2
        Slow ~ 100 WPM → adjustment = 0.7
        """
        if wpm is None:
            return 1.0  # Default
        
        # Normal speed is about 150 WPM
        normalized = np.clip((wpm / 150), 0.5, 2.0)
        
        return normalized
    
    def save_profile(self, user_id, output_dir, format='json'):
        if user_id not in self.voice_profiles:
            logger.error(f"No profile found for user {user_id}")
            return None
        
        profile = self.voice_profiles[user_id]
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            filepath = output_dir / f"{user_id}_profile.json"
            profile.save_json(filepath)
        elif format == 'yaml':
            filepath = output_dir / f"{user_id}_profile.yaml"
            profile.save_yaml(filepath)
        else:
            logger.error(f"Unknown format: {format}")
            return None
        
        logger.info(f"Profile saved to {filepath}")
        
        return filepath
    
    def load_profile(self, profile_path):
        
        try:
            with open(profile_path, 'r') as f:
                if profile_path.endswith('.json'):
                    data = json.load(f)
                elif profile_path.endswith('.yaml'):
                    data = yaml.safe_load(f)
                else:
                    logger.error("Unsupported file format")
                    return None
            
            # Reconstruct profile from data
            profile = VoiceProfile(
                user_id=data['user_id'],
                user_name=data['user_name']
            )
            
            sc = data['speaking_characteristics']
            profile.speaking_rate_wpm = sc['speaking_rate_wpm']
            profile.average_pause_duration = sc['average_pause_duration']
            profile.mean_pitch = sc['mean_pitch']
            profile.pitch_range = sc['pitch_range']
            
            self.voice_profiles[profile.user_id] = profile
            
            logger.info(f"Profile loaded for user {profile.user_id}")
            
            return profile
        
        except Exception as e:
            logger.error(f"Error loading profile: {str(e)}")
            return None

    def _infer_emotion(self, profile: VoiceProfile) -> dict:

        mean_pitch = profile.mean_pitch or 0.0
        pitch_range = 0.0
        if profile.pitch_range and len(profile.pitch_range) == 2:
            pitch_range = profile.pitch_range[1] - profile.pitch_range[0]

        speaking_rate = profile.speaking_rate_wpm or 0.0

        # crude energy estimate
        if profile.energy_levels:
            avg_energy = sum(profile.energy_levels) / len(profile.energy_levels)
        else:
            avg_energy = 0.0

        rules_triggered = []

        # thresholds
        HIGH_PITCH = 200.0
        LOW_PITCH = 130.0
        HIGH_RANGE = 80.0
        LOW_RANGE = 40.0
        FAST_RATE = 160.0
        SLOW_RATE = 110.0
        HIGH_ENERGY = 45.0
        LOW_ENERGY = 35.0

        # Rule scores
        scores = {
            "happy": 0,
            "sad": 0,
            "angry": 0,
            "calm": 0,
            "neutral": 0,
        }

        # Happy / excited: higher pitch, larger pitch range, higher energy, faster speech
        if mean_pitch > HIGH_PITCH:
            scores["happy"] += 1
            scores["angry"] += 0.5
            rules_triggered.append("high_mean_pitch")
        if pitch_range > HIGH_RANGE:
            scores["happy"] += 1
            scores["angry"] += 1
            rules_triggered.append("large_pitch_range")
        if speaking_rate > FAST_RATE:
            scores["happy"] += 0.5
            scores["angry"] += 0.5
            rules_triggered.append("fast_speaking_rate")
        if avg_energy > HIGH_ENERGY:
            scores["angry"] += 1
            scores["happy"] += 0.5
            rules_triggered.append("high_energy")

        # Sad: lower pitch, small range, slow, low energy
        if mean_pitch < LOW_PITCH:
            scores["sad"] += 1
            rules_triggered.append("low_mean_pitch")
        if pitch_range < LOW_RANGE:
            scores["sad"] += 0.5
            scores["calm"] += 0.5
            rules_triggered.append("small_pitch_range")
        if speaking_rate < SLOW_RATE:
            scores["sad"] += 0.5
            scores["calm"] += 0.5
            rules_triggered.append("slow_speaking_rate")
        if avg_energy < LOW_ENERGY:
            scores["sad"] += 0.5
            scores["calm"] += 0.5
            rules_triggered.append("low_energy")

        # Calm vs neutral: mid‑values
        if LOW_PITCH <= mean_pitch <= HIGH_PITCH and LOW_RANGE <= pitch_range <= HIGH_RANGE:
            scores["neutral"] += 0.5
            rules_triggered.append("mid_pitch_mid_range")
        if SLOW_RATE < speaking_rate < FAST_RATE and LOW_ENERGY < avg_energy < HIGH_ENERGY:
            scores["calm"] += 0.5
            scores["neutral"] += 0.5
            rules_triggered.append("mid_rate_mid_energy")

        # pick the best
        dominant = max(scores, key=scores.get)
        max_score = scores[dominant]

        # simple confidence: normalized max score
        total = sum(scores.values()) or 1.0
        confidence = max_score / total

        return {
            "dominant_emotion": dominant,
            "confidence": round(confidence, 2),
            "scores": scores,
            "rules_triggered": rules_triggered,
            "features_used": {
                "mean_pitch": mean_pitch,
                "pitch_range": pitch_range,
                "speaking_rate_wpm": speaking_rate,
                "avg_energy": avg_energy,
            },
        }

   
# MAIN FUNCTION

def main():

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('personalization.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create engine
    engine = PersonalizationEngine(sr=22050)
    
    try:
        # 1: Create profile from audio file
        print("\n[Step 1] Creating voice profile from audio")
        profile = engine.create_voice_profile(
            user_id="user_001",
            user_name="Test User 1",
            audio_path="user_audio.mp3" 
        )
        
        if profile:
            print(f"  Profile created for {profile.user_name}")
            print(f"  Speaking rate: {profile.speaking_rate_wpm:.1f} WPM")
            print(f"  Mean pitch: {profile.mean_pitch:.1f} Hz")
            print(f"  Pitch range: {profile.pitch_range[0]:.1f} - {profile.pitch_range[1]:.1f} Hz")
            
            # 2: Get synthesis parameters
            print("\n[Step 2] Getting synthesis parameters")
            params = engine.get_synthesis_parameters("user_001")
            if params:
                print(f"Synthesis parameters:")
                for key, value in params.items():
                    print(f"    {key}: {value}")
            
            # 3: Save profile
            print("\n[Step 3] Saving profile")
            engine.save_profile("user_001", "./profiles", format='json')
            print("Profile saved")
            
            # 4: Load profile
            print("\n[Step 4] Loading profile")
            loaded = engine.load_profile("./profiles/user_001_profile.json")
            if loaded:
                print(f"Profile loaded for {loaded.user_name}")
    
    except FileNotFoundError:
        print("\nNote: Please provide a user audio file named 'user_audio.mp3'")
    except Exception as e:
        print(f"\nError: {str(e)}")


if __name__ == "__main__":
    main()
