import wave, struct, math, random, os
from pathlib import Path

audio_dir = Path('android-app/www/assets/audio')
audio_dir.mkdir(parents=True, exist_ok=True)

def create_wav(filename, duration=1.0, freq=440, sample_rate=22050, wave_type='sine'):
    nframes = int(duration * sample_rate)
    wav_file = wave.open(str(audio_dir / filename), 'w')
    wav_file.setparams((1, 2, sample_rate, nframes, 'NONE', 'not compressed'))
    for i in range(nframes):
        t = i / sample_rate
        envelope = min(1.0, t * 4) * min(1.0, (duration - t) * 4)
        if wave_type == 'sine':
            value = math.sin(2 * math.pi * freq * t)
        elif wave_type == 'square':
            value = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        elif wave_type == 'sawtooth':
            value = 2 * ((freq * t) % 1) - 1
        elif wave_type == 'triangle':
            value = 2 * abs(2 * ((freq * t) % 1) - 1) - 1
        elif wave_type == 'noise':
            value = random.uniform(-1, 1)
        else:
            value = math.sin(2 * math.pi * freq * t)
        value = int(32767 * envelope * value)
        wav_file.writeframes(struct.pack('<h', value))
    wav_file.close()

# Generate large BGM tracks (10 tracks x 120 sec each = ~26 MB)
for i in range(10):
    freq_base = [110, 130.81, 146.83, 164.81, 196.00, 220, 261.63, 293.66, 329.63, 392.00][i]
    create_wav(f'bgm_{i}.wav', duration=120.0, freq=freq_base, wave_type='sine')
    print(f'Created bgm_{i}.wav (120s)')

# Generate SFX with longer durations (30 effects x 10 sec = ~1.3 MB)
for i in range(30):
    freq = random.randint(200, 2000)
    wave_types = ['sine', 'square', 'sawtooth', 'triangle', 'noise']
    wtype = wave_types[i % len(wave_types)]
    create_wav(f'sfx_{i}.wav', duration=10.0, freq=freq, wave_type=wtype)
    if i % 10 == 0:
        print(f'Created {i+1} SFX')

# Generate ambient tracks (10 tracks x 120 sec = ~26 MB)
for i in range(10):
    freq = [80, 100, 120, 150, 180, 200, 220, 240, 260, 280][i]
    create_wav(f'ambient_{i}.wav', duration=120.0, freq=freq, wave_type='sine')
    print(f'Created ambient_{i}.wav (120s)')

# Generate voice samples (20 tracks x 30 sec = ~2.6 MB)
for i in range(20):
    freq = random.randint(300, 800)
    create_wav(f'voice_{i}.wav', duration=30.0, freq=freq, wave_type='triangle')
    if i % 5 == 0:
        print(f'Created {i+1} voice samples')

total_size = sum(f.stat().st_size for f in audio_dir.iterdir() if f.suffix == '.wav')
print(f'\nTotal audio size: {total_size / 1024 / 1024:.1f} MB')
print('Audio generation complete')