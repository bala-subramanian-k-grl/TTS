# Technical Architecture Documentation

## System Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                    PERSONALIZATION SYSTEM                      │
│          (Extends Piper TTS with Voice Learning)               │
└────────────────────────────────────────────────────────────────┘

INPUT LAYER:
┌──────────────┐
│  User Audio  │  (WAV, MP3, FLAC files)
│  Recording   │  5-10 minutes of speech
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ PREPROCESSING LAYER                                             │
├─────────────────────────────────────────────────────────────────┤
│ • AudioPreprocessor                                             │
│   ├─ Load audio file                                           │
│   ├─ Remove silence (trim edges)                               │
│   ├─ Normalize volume to consistent level                      │
│   ├─ Reduce background noise                                   │
│   └─ Output: Clean audio ready for analysis                    │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ ANALYSIS LAYER                                                  │
├─────────────────────────────────────────────────────────────────┤
│ • FeatureExtractor                                              │
│   ├─ Extract Energy (loudness over time)                       │
│   ├─ Extract Pitch (fundamental frequency F0)                  │
│   ├─ Extract Pauses (silence detection)                        │
│   ├─ Calculate Speaking Rate (WPM)                             │
│   └─ Output: SpeakingPatterns object                           │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ PROFILE CREATION LAYER                                          │
├─────────────────────────────────────────────────────────────────┤
│ • VoiceProfile                                                  │
│   ├─ Store user metadata (ID, name, timestamp)                 │
│   ├─ Store extracted features                                  │
│   ├─ Store raw audio characteristics                           │
│   └─ Output: Profile object (JSON)                        │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ SYNTHESIS LAYER                                                 │
├─────────────────────────────────────────────────────────────────┤
│ • TTS Adapter / Synthesis Parameters                            │
│   ├─ Convert pitch to Piper parameters                         │
│   ├─ Convert speed to Piper parameters                         │
│   ├─ Map pauses to synthesis timing                            │
│   └─ Output: Parameters for Piper TTS                          │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ PIPER TTS (External)                                            │
├─────────────────────────────────────────────────────────────────┤
│ • Text → Personalized Audio                                     │
│   Input: Text + Personalization Parameters                     │
│   Output: Synthesized audio with user's voice characteristics  │
└──────┬───────────────────────────────────────────────────────────┘
       │
       ▼
    OUTPUT: Personalized Speech Audio
```

---

## Component Details

### 1. AudioPreprocessor Component

**Purpose:** Clean and prepare raw audio recordings

**Inputs:**

- `audio_path`: String path to audio file (WAV, MP3, FLAC)
- Audio file on disk

**Processing Steps:**

```
Step 1: Load
  Input: audio_path (string)
  Process: librosa.load(audio_path, sr=22050)
  Output: audio array, sample rate

Step 2: Remove Silence
  Input: audio array
  Process: librosa.effects.trim(audio, top_db=20)
  Output: trimmed audio (no leading/trailing silence)

Step 3: Normalize
  Input: trimmed audio
  Process: audio / max(abs(audio))
  Output: audio with peak amplitude = 1.0

Step 4: Reduce Noise
  Input: normalized audio
  Process: Simple spectral subtraction
  Output: cleaner audio
```

**Outputs:**

- Clean audio array (numpy array)
- Sample rate (Hz)
- Optionally saves preprocessed audio to file

**Key Metrics Logged:**

- Audio duration (seconds)
- Sample rate (Hz)
- Total samples
- Silence removed (samples)
- Normalization factor

---

### 2. FeatureExtractor Component

**Purpose:** Extract speaking patterns from audio

**Inputs:**

- `audio`: Clean audio array from preprocessor
- `sr`: Sample rate (22050 Hz)

**Feature Extraction Methods:**

#### A. Energy Extraction

```
What: How loud is the audio at each time point?
How:
  1. Break audio into frames (2048 samples = ~93ms at 22050 Hz)
  2. Move frames by 512 samples each time
  3. Calculate energy of each frame (mel-spectrogram)
  4. Convert to decibels
Output: Energy array (1 value per frame)

Example:
  Frame 1: 35 dB (quiet)
  Frame 2: 42 dB (medium)
  Frame 3: 40 dB (medium)
  ...
```

#### B. Pitch Extraction

```
What: What's the fundamental frequency (how high/low)?
How:
  1. Use PYIN algorithm (probabilistic YIN)
  2. Detect F0 (fundamental frequency) at each frame
  3. Only keep voiced frames (actual speech)
  4. Calculate statistics
Output: Pitch values (Hz), pitch range, mean pitch

Example:
  Mean pitch: 115 Hz (male voice)
  Range: 85-180 Hz
  Std deviation: 25 Hz (variation)
```

#### C. Pause Detection

```
What: Where does the person pause/be silent?
How:
  1. Set energy threshold (25th percentile of energy values)
  2. Find frames below threshold
  3. Group consecutive frames
  4. Calculate pause durations
Output: List of pause durations

Example:
  Pause 1: 0.52 seconds
  Pause 2: 0.48 seconds
  Pause 3: 0.61 seconds
```

#### D. Speaking Rate Calculation

```
What: How fast is the person speaking (words per minute)?
How:
  1. Total audio duration
  2. Subtract pause times
  3. Estimate words (2.5 words/second typical)
  4. Convert to WPM
Output: Speaking rate (words per minute)

Formula:
  speaking_time = total_duration - sum(pause_durations)
  estimated_words = speaking_time * 2.5
  estimated_wpm = (estimated_words / speaking_time) * 60

Example:
  Total: 300 seconds
  Pauses: 30 seconds
  Speaking time: 270 seconds
  Estimated words: 675
  Result: 150 WPM
```

**Outputs:**

- `SpeakingPatterns` object containing:
  - `speaking_rate_wpm`: float
  - `average_pause_duration`: float
  - `energy_levels`: list of floats
  - `pitch_contour`: list of floats
  - `mean_pitch`: float
  - `pitch_range`: tuple (min, max)

---

### 3. PersonalizationEngine Component

**Purpose:** Orchestrate learning and profile creation

**Inputs:**

- `user_id`: Unique identifier for user
- `user_name`: Human-readable name
- `audio_path`: Path to user's audio file

**Processing Steps:**

```
Step 1: Load & Preprocess
  ├─ Call AudioPreprocessor.preprocess()
  └─ Output: clean audio

Step 2: Extract Features
  ├─ Call FeatureExtractor.extract_all_features()
  └─ Output: SpeakingPatterns

Step 3: Create Profile
  ├─ Create VoiceProfile object
  ├─ Populate with:
  │  ├─ User metadata (ID, name, timestamp)
  │  ├─ Speaking characteristics
  │  ├─ Raw audio features
  │  └─ Emotion profile (if available)
  └─ Output: VoiceProfile

Step 4: Convert to Synthesis Parameters
  ├─ Normalize pitch (Hz → 0.5-2.0 factor)
  ├─ Normalize speed (WPM → 0.5-2.0 factor)
  ├─ Prepare pause durations
  └─ Output: Parameters dict for Piper
```

**Outputs:**

- `VoiceProfile` object
- Synthesis parameters dict
- Profile saved as JSON/YAML

**Storage Format:**

```
VoiceProfile Structure:
{
  "user_id": "user_001",
  "user_name": "John Doe",
  "created_date": "2025-01-15T10:30:00",
  "last_updated": "2025-01-15T10:30:00",
  "speaking_characteristics": {
    "speaking_rate_wpm": 145.3,
    "average_pause_duration": 0.52,
    "mean_pitch": 115.4,
    "pitch_range": [85.2, 180.5]
  },
  "emotion_profile": {}
}
```

---

## Data Flow Diagram

```
User Audio Input
      ↓
┌─────────────────────────┐
│ Audio Preprocessor      │
│ (Clean audio)           │
└──────────┬──────────────┘
           ↓
    [Clean Audio]
           ↓
┌─────────────────────────┐
│ Feature Extractor       │
│ (Extract patterns)      │
└──────────┬──────────────┘
           ↓
    [SpeakingPatterns]
    ├─ speaking_rate
    ├─ pitch data
    ├─ pause durations
    └─ energy levels
           ↓
┌─────────────────────────┐
│ Profile Creator         │
│ (Create user profile)   │
└──────────┬──────────────┘
           ↓
    [VoiceProfile]
    (JSON/YAML)
           ↓
┌─────────────────────────┐
│ Synthesis Adapter       │
│ (Convert for Piper)     │
└──────────┬──────────────┘
           ↓
    [Synthesis Params]
    ├─ pitch_adjust: 0.77
    ├─ speed_adjust: 0.97
    └─ pause: 0.52
           ↓
┌─────────────────────────┐
│ Piper TTS               │
│ (Synthesize speech)     │
└──────────┬──────────────┘
           ↓
    OUTPUT: Personalized Audio
```

---

## Performance Metrics

### Time Complexity

```
Operation                    Time Complexity
─────────────────────────────────────────────
Load audio                   O(n) - read file
Preprocess (normalize)       O(n) - single pass
Energy extraction            O(n log n) - FFT
Pitch extraction (PYIN)      O(n²) - iterative algorithm
Pause detection              O(n) - linear scan
Speaking rate calc           O(n) - linear pass
─────────────────────────────────────────────
Total: O(n²) dominated by PYIN pitch detection

Where n = audio length in samples
```

### Space Complexity

```
Component                    Space Used
─────────────────────────────────────────
Audio array                  O(n) - stores samples
Energy array                 O(n/512) ~ O(n)
Pitch array                  O(n/512) ~ O(n)
Spectrogram matrix           O(128 × n/512) ~ O(n)
─────────────────────────────────────────
Total: O(n)

For 5-minute audio at 22050 Hz:
  n = 22050 × 60 × 5 = 6,615,000 samples
  Memory = ~50-100 MB depending on implementation
```

### Typical Processing Time

```
5-minute Audio File Processing:

Audio Loading:          ~0.5 seconds
Silence Removal:        ~0.2 seconds
Normalization:          ~0.1 seconds
Energy Extraction:      ~0.3 seconds
Pitch Extraction:       ~15-30 seconds (PYIN is slow)
Pause Detection:        ~0.2 seconds
Speaking Rate Calc:     ~0.1 seconds
─────────────────────────────
Total:                  ~16-31 seconds

Optimization notes:
- Pitch extraction is the bottleneck
- Could use faster but less accurate algorithms
- Could parallelize if multiple users processed
```

---

## Integration with Piper TTS

### Piper TTS Parameter Mapping

```
Our Learning          →  Piper Parameter  →  Effect
─────────────────────────────────────────────────────
Mean pitch: 115 Hz    →  pitch: 0.77      →  Lower voice
Speaking rate: 145    →  speed: 0.97      →  Normal speed
Pause: 0.52s          →  pause: 0.52      →  Natural pauses
Energy: 65 dB         →  volume: 0.75     →  Quieter

Normalization Formula:
  pitch_factor = mean_pitch / 150 (clamped to 0.5-2.0)
  speed_factor = wpm / 150 (clamped to 0.5-2.0)
```

### Usage with Piper

```python
# Step 1: Get personalization parameters
params = engine.get_synthesis_parameters("user_001")

# Step 2: Initialize Piper with parameters
voice = PiperVoice.load(model_path)

# Step 3: Synthesize with parameters
audio = voice.synthesize(
    text="Hello world",
    speaker=None,
    length_scale=params['speaking_rate_adjust'],
    noise_scale=0.667,
    noise_w=0.8
)
```

---

## Logging System

### Log Levels

```
DEBUG   - Detailed debugging info (frame-level data)
INFO    - General information (processing steps, results)
WARNING - Warnings (unusual but handled)
ERROR   - Errors (processing failed)
```

### Log Format

```
TIMESTAMP - MODULE - LEVEL - MESSAGE

Example:
2025-01-15 10:30:45 - audio_preprocessor - INFO - Loaded audio: user_001.wav
2025-01-15 10:30:46 - feature_extractor - INFO - Pitch extraction: 1950 voiced frames
```

### What Gets Logged

```
Audio Loading:
  ✓ File path, format, size
  ✓ Audio duration, sample rate, channels
  ✓ Any load errors

Preprocessing:
  ✓ Silence removed (samples count)
  ✓ Normalization factor
  ✓ Noise reduction applied

Feature Extraction:
  ✓ Energy: number of frames, range, statistics
  ✓ Pitch: number of voiced frames, range, mean, std
  ✓ Pauses: number found, average duration
  ✓ Speaking rate: WPM calculation

Profile Creation:
  ✓ User ID, name, timestamp
  ✓ All extracted features
  ✓ Save location and format

Performance:
  ✓ Processing time for each step
  ✓ Memory usage (where feasible)
  ✓ Total end-to-end time
```

---

## Error Handling

### Common Errors

```
Error                           Handling
────────────────────────────────────────────────
File not found                  Log error, raise exception
Audio format unsupported        Log warning, try librosa default
Audio too short                 Log warning, continue with available
Audio too quiet                 Log warning, attempt normalization
No pitch detected               Log error, return None
Invalid profile format          Log error, skip profile
Insufficient permissions        Log error, raise exception
```

---

## Extension Points

### How to Extend the System

```
1. Add Emotion Recognition
   ├─ File: emotion_detector.py
   ├─ Input: audio
   ├─ Output: emotion labels + confidence
   └─ Integrate into FeatureExtractor

2. Add Accent Detection
   ├─ File: accent_analyzer.py
   ├─ Input: pitch + spectral features
   ├─ Output: accent classification
   └─ Store in VoiceProfile.emotion_profile

3. Add Fine-tuning Support
   ├─ File: model_finetuner.py
   ├─ Input: user audio + Piper base model
   ├─ Output: fine-tuned Piper model
   └─ Add method to PersonalizationEngine

4. Add REST API
   ├─ File: api.py (using FastAPI)
   ├─ Endpoints: /create_profile, /synthesize, /load_profile
   ├─ Return: JSON responses
   └─ Add authentication layer
```

---

## Quality Assurance

### Testing Strategy

```
Unit Tests:
  ✓ Audio loading and formats
  ✓ Silence removal algorithm
  ✓ Feature extraction accuracy
  ✓ Profile creation and storage
  ✓ Parameter normalization

Integration Tests:
  ✓ Full pipeline (audio → profile)
  ✓ Save and load profile
  ✓ Multiple users simultaneously

Performance Tests:
  ✓ Processing time benchmarks
  ✓ Memory usage monitoring
  ✓ Scalability with audio length
```

---

## Conclusion

This architecture provides a modular, extensible system for learning voice characteristics from user audio and applying them to Piper TTS synthesis. Each component has clear inputs/outputs, and the system is designed for easy extension and modification.
