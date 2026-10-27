import wave, struct, math, random
from pathlib import Path

audio_dir = Path('android-app/www/assets/audio')
audio_dir.mkdir(parents=True, exist_ok=True)

def create_wav(filename, duration=1.0, freq=440, sample_rate=22050):
    nframes = int(duration * sample_rate)
    wav_file = wave.open(str(audio_dir / filename), 'w')
    wav_file.setparams((1, 2, sample_rate, nframes, 'NONE', 'not compressed'))
    for i in range(nframes):
        t = i / sample_rate
        envelope = min(1.0, t * 4) * min(1.0, (duration - t) * 4)
        value = int(32767 * envelope * math.sin(2 * math.pi * freq * t))
        wav_file.writeframes(struct.pack('<h', value))
    wav_file.close()

# Create fewer but longer files to get size
# BGM: 5 tracks x 60 sec = 5 * 60 * 22050 * 2 bytes = ~13 MB
for i in range(5):
    create_wav(f'bgm_{i}.wav', duration=60.0, freq=110 * (i % 7 + 1))
    print(f'Created bgm_{i}.wav')

# SFX: 20 effects x 2 sec = 20 * 2 * 22050 * 2 = ~1.7 MB
for i in range(20):
    freq = random.randint(200, 2000)
    create_wav(f'sfx_{i}.wav', duration=2.0, freq=freq)

# UI: 10 sounds x 0.5 sec = ~0.2 MB
for i in range(10):
    create_wav(f'ui_{i}.wav', duration=0.5, freq=800 + i * 50)

# Ambient: 3 tracks x 60 sec = ~3.9 MB
for i in range(3):
    create_wav(f'ambient_{i}.wav', duration=60.0, freq=80 + i * 20)

print('Audio generation complete')