"""
1. Setup - Initialize the system
2. Learning - Process user audio
3. Creation - Create voice profile
4. Synthesis - Get parameters for TTS
5. Storage - Save profile for later use
"""

import logging
import sys
from pathlib import Path
from personalization_engine import PersonalizationEngine

# Setup logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('personalization.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def print_header(text):
    print(f"  {text}")

def print_section(text):
    print(f"\n {text}")

def main():
        
    print_header("PIPER TTS PERSONALIZATION ENGINE")
    # STEP 1: INITIALIZE ENGINE
    
    print_section("Initializing Engine")
    
    try:
        engine = PersonalizationEngine(sr=22050)
        print("Engine initialized successfully")
        print(f"  Sample rate: 22050 Hz (CD quality)")
    except Exception as e:
        print(f"Error initializing engine: {e}")
        return False
    
    # CREATE VOICE PROFILE
 
    profile = engine.create_voice_profile(
        user_id="user1",
        user_name="User 1",
        audio_path="user_audio.mp3",  
    )
   
    engine.voice_profiles["user1"] = profile
    
    print("   Example profile created")
    print(f"  User: {profile.user_name}")
    print(f"  Speaking rate: {profile.speaking_rate_wpm:.1f} WPM")
    print(f"  Mean pitch: {profile.mean_pitch:.1f} Hz")
    print(f"  Pitch range: {profile.pitch_range[0]:.1f} - {profile.pitch_range[1]:.1f} Hz")
    
    # STEP 3: ANALYZE PROFILE
    
    print_section("Analyzing Profile")
    
    print("Profile characteristics:")
    print(f"  • Speaking Rate: {profile.speaking_rate_wpm:.1f} words per minute")
    print(f"    (Normal: 100-150 WPM)")
    print()
    print(f"  • Mean Pitch: {profile.mean_pitch:.1f} Hz")
    print(f"    (Male: 85-180 Hz, Female: 165-255 Hz)")
    print()
    print(f"  • Pitch Range: {profile.pitch_range[1] - profile.pitch_range[0]:.1f} Hz")
    print(f"    (More range = more expressive)")
    print()
    print(f"  • Average Pause: {profile.average_pause_duration:.3f} seconds")
    print(f"    (Natural pauses: 0.3-1.0 seconds)")

    # GET SYNTHESIS PARAMETERS
    
    print_section("Generating Synthesis Parameters")
    
    params = engine.get_synthesis_parameters("user1")
    
    if params:
        print("Synthesis parameters for Piper TTS:")
        print()
        print(f"  • Pitch Adjustment: {params['pitch_adjust']:.2f}")
        print(f"    (0.5 = lower, 1.0 = normal, 2.0 = higher)")
        print()
        print(f"  • Speed Adjustment: {params['speaking_rate_adjust']:.2f}")
        print(f"    (0.5 = slower, 1.0 = normal, 2.0 = faster)")
        print()
        print(f"  • Pause Duration: {params['pause_duration']:.3f} seconds")
        print()
        print(f"  • Energy Level: {params['energy_level']:.2f}")
        print(f"    (How loud the synthesized speech will be)")
        
        print("\nParameters ready to use with Piper TTS")
    else:
        print("Failed to generate parameters")
        return False

    # SAVE PROFILE
    
    print_section("Saving Profile")
    
    try:
        profiles_dir = Path("./profiles")
        profiles_dir.mkdir(exist_ok=True)
        # Save as JSON
        json_path = engine.save_profile("user1",str(profiles_dir), format='json')
        print(f"Profile saved as JSON:")
        print(f"  {json_path}")
        
        # Show file contents
        print("\nProfile JSON structure:")
        with open(json_path, 'r') as f:
            import json
            data = json.load(f)
            print(json.dumps(data, indent=2))
    
    except Exception as e:
        print(f"Error saving profile: {e}")
        return False
    
    # LOAD PROFILE

    print_section("Loading Profile")
    
    try:
        # Clear profiles to show loading works
        engine.voice_profiles.clear()
        
        # Load profile
        loaded = engine.load_profile(str(json_path))
        
        if loaded:
            print(f"  Profile loaded successfully")
            print(f"  User ID: {loaded.user_id}")
            print(f"  User Name: {loaded.user_name}")
            print(f"  Created: {loaded.created_date}")
            print(f"  Speaking rate: {loaded.speaking_rate_wpm:.1f} WPM")
        else:
            print("Failed to load profile")
            return False
    
    except Exception as e:
        print(f"Error loading profile: {e}")
        return False
    return True
   
if __name__ == "__main__":
    try:
        success = main()
        
        if success:
            print("  EXECUTION COMPLETE")
            sys.exit(0)
        else:
            print("  EXECUTION FAILED")
            sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nError: {e}")
        sys.exit(1)

