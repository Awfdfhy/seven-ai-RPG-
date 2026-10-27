import os, random
from pathlib import Path

assets_dir = Path('android-app/www/assets')

try:
    from PIL import Image, ImageDraw, ImageFont
    
    img_dir = assets_dir / 'images'
    img_dir.mkdir(parents=True, exist_ok=True)
    
    # Character sprites (8 classes x 4 directions x 4 frames = 128 sprites)
    for cls in ['warrior', 'mage', 'rogue', 'cleric', 'ranger', 'paladin', 'warlock', 'monk']:
        for direction in ['down', 'up', 'left', 'right']:
            for frame in range(4):
                img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
                draw = ImageDraw.Draw(img)
                colors = {'warrior': (200,50,50), 'mage': (50,50,200), 'rogue': (50,200,50), 
                         'cleric': (200,200,50), 'ranger': (100,150,50), 'paladin': (200,150,50),
                         'warlock': (150,50,200), 'monk': (100,200,200)}
                color = colors.get(cls, (100,100,100))
                draw.rectangle([16, 16, 48, 48], fill=color + (200,))
                draw.text((20, 24), f'{cls[0]}{direction[0]}{frame}', fill=(255,255,255,255))
                img.save(img_dir / f'char_{cls}_{direction}_{frame}.png')
    
    # Enemy sprites (50 types x 2 frames)
    for i in range(50):
        for frame in range(2):
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            color = (random.randint(50,200), random.randint(50,200), random.randint(50,200))
            draw.ellipse([8, 8, 56, 56], fill=color + (200,))
            draw.text((24, 24), f'E{i}{frame}', fill=(255,255,255,255))
            img.save(img_dir / f'enemy_{i}_{frame}.png')
    
    # Item icons (500 items)
    for i in range(500):
        img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        categories = ['weapon', 'armor', 'accessory', 'consumable', 'material', 'quest']
        cat = categories[i % len(categories)]
        cat_colors = {'weapon': (200,100,100), 'armor': (100,100,200), 'accessory': (200,200,100),
                     'consumable': (100,200,100), 'material': (150,150,150), 'quest': (200,100,200)}
        color = cat_colors[cat]
        draw.rectangle([4, 4, 28, 28], fill=color + (220,))
        draw.text((8, 8), str(i), fill=(255,255,255,255))
        img.save(img_dir / f'item_{i:04d}.png')
    
    # Background images (20 regions)
    for i in range(20):
        img = Image.new('RGBA', (1024, 768), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        for y in range(768):
            r = int(20 + (y / 768) * 40)
            g = int(15 + (y / 768) * 30)
            b = int(30 + (y / 768) * 50)
            draw.line([(0, y), (1024, y)], fill=(r, g, b, 255))
        for _ in range(50):
            x = random.randint(0, 1024)
            y = random.randint(0, 768)
            size = random.randint(5, 30)
            draw.ellipse([x, y, x+size, y+size], fill=(255, 255, 200, 100))
        draw.text((50, 50), f'Region {i} Background', fill=(255,255,255,255))
        img.save(img_dir / f'bg_region_{i}.png')
    
    # UI icons (100 icons)
    for i in range(100):
        img = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([4, 4, 44, 44], radius=8, fill=(60, 60, 80, 220))
        draw.text((16, 16), f'UI{i}', fill=(200,200,200,255))
        img.save(img_dir / f'ui_icon_{i}.png')
    
    # Tile sets (10 tilesets x 16 tiles)
    for ts in range(10):
        for tile in range(16):
            img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            color = (random.randint(40,120), random.randint(40,120), random.randint(40,120))
            draw.rectangle([0, 0, 32, 32], fill=color + (255,))
            for x in range(0, 32, 8):
                for y in range(0, 32, 8):
                    if (x + y) % 16 == 0:
                        draw.rectangle([x, y, x+4, y+4], fill=(color[0]+40, color[1]+40, color[2]+40, 255))
            img.save(img_dir / f'tileset_{ts}_tile_{tile}.png')
    
    # Character portraits (8 classes x 3 variants = 24)
    for cls in ['warrior', 'mage', 'rogue', 'cleric', 'ranger', 'paladin', 'warlock', 'monk']:
        for variant in range(3):
            img = Image.new('RGBA', (256, 256), (20, 20, 30, 255))
            draw = ImageDraw.Draw(img)
            colors = {'warrior': (200,50,50), 'mage': (50,50,200), 'rogue': (50,200,50), 
                     'cleric': (200,200,50), 'ranger': (100,150,50), 'paladin': (200,150,50),
                     'warlock': (150,50,200), 'monk': (100,200,200)}
            color = colors.get(cls, (100,100,100))
            draw.ellipse([64, 20, 192, 148], fill=color + (200,))
            draw.rectangle([80, 148, 176, 236], fill=tuple(min(c+30, 255) for c in color) + (200,))
            draw.text((80, 100), f'{cls.title()} {variant+1}', fill=(255,255,255,255))
            img.save(img_dir / f'portrait_{cls}_{variant}.png')
    
    print('Images created successfully')
    
except ImportError:
    print('PIL not available, creating empty placeholder files...')
    img_dir = assets_dir / 'images'
    img_dir.mkdir(parents=True, exist_ok=True)
    for cls in ['warrior', 'mage', 'rogue', 'cleric', 'ranger', 'paladin', 'warlock', 'monk']:
        for direction in ['down', 'up', 'left', 'right']:
            for frame in range(4):
                (img_dir / f'char_{cls}_{direction}_{frame}.png').write_bytes(b'')
    for i in range(50):
        for frame in range(2):
            (img_dir / f'enemy_{i}_{frame}.png').write_bytes(b'')
    for i in range(500):
        (img_dir / f'item_{i:04d}.png').write_bytes(b'')
    for i in range(20):
        (img_dir / f'bg_region_{i}.png').write_bytes(b'')
    for i in range(100):
        (img_dir / f'ui_icon_{i}.png').write_bytes(b'')
    for ts in range(10):
        for tile in range(16):
            (img_dir / f'tileset_{ts}_tile_{tile}.png').write_bytes(b'')
    for cls in ['warrior', 'mage', 'rogue', 'cleric', 'ranger', 'paladin', 'warlock', 'monk']:
        for variant in range(3):
            (img_dir / f'portrait_{cls}_{variant}.png').write_bytes(b'')
    print('Empty placeholder files created')

print('Image generation complete')