import os, random, json
from pathlib import Path

assets_dir = Path('android-app/www/assets')
img_dir = assets_dir / 'images'
data_dir = assets_dir / 'data'
img_dir.mkdir(parents=True, exist_ok=True)
data_dir.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Create HD background images (1920x1080) - 20 images
    for i in range(20):
        img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        for y in range(1080):
            r = int(10 + (y / 1080) * 50)
            g = int(5 + (y / 1080) * 40)
            b = int(20 + (y / 1080) * 60)
            draw.line([(0, y), (1920, y)], fill=(r, g, b, 255))
        for _ in range(200):
            x = random.randint(0, 1920)
            y = random.randint(0, 1080)
            size = random.randint(10, 100)
            draw.ellipse([x, y, x+size, y+size], fill=(255, 255, 200, 50))
        draw.text((100, 100), f'Region {i} HD Background', fill=(255,255,255,255))
        img.save(img_dir / f'hd_bg_region_{i}.png')
    
    # Create large sprite sheets (2048x2048) - 10 sheets
    for i in range(10):
        img = Image.new('RGBA', (2048, 2048), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for row in range(8):
            for col in range(8):
                x = col * 256
                y = row * 256
                color = (random.randint(50,200), random.randint(50,200), random.randint(50,200))
                draw.rectangle([x+10, y+10, x+246, y+246], fill=color + (200,))
                draw.text((x+100, y+110), f'S{i}R{row}C{col}', fill=(255,255,255,255))
        img.save(img_dir / f'spritesheet_{i}.png')
    
    # Create large item icons (256x256) - 200 icons
    for i in range(200):
        img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        categories = ['weapon', 'armor', 'accessory', 'consumable', 'material', 'quest']
        cat = categories[i % len(categories)]
        cat_colors = {'weapon': (200,100,100), 'armor': (100,100,200), 'accessory': (200,200,100),
                     'consumable': (100,200,100), 'material': (150,150,150), 'quest': (200,100,200)}
        color = cat_colors[cat]
        draw.rounded_rectangle([20, 20, 236, 236], radius=40, fill=color + (220,))
        draw.text((80, 100), f'Item {i}', fill=(255,255,255,255))
        img.save(img_dir / f'large_item_{i:03d}.png')
    
    # Create large portraits (512x512) - 50 portraits
    for i in range(50):
        img = Image.new('RGBA', (512, 512), (20, 20, 30, 255))
        draw = ImageDraw.Draw(img)
        color = (random.randint(50,200), random.randint(50,200), random.randint(50,200))
        draw.ellipse([106, 40, 406, 296], fill=color + (200,))
        draw.rectangle([128, 296, 384, 472], fill=tuple(min(c+30, 255) for c in color) + (200,))
        draw.text((156, 200), f'Portrait {i}', fill=(255,255,255,255))
        img.save(img_dir / f'large_portrait_{i:03d}.png')
    
    # Create large tile textures (512x512) - 50 tiles
    for i in range(50):
        img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        color = (random.randint(40,120), random.randint(40,120), random.randint(40,120))
        draw.rectangle([0, 0, 512, 512], fill=color + (255,))
        for x in range(0, 512, 32):
            for y in range(0, 512, 32):
                if (x + y) % 64 == 0:
                    draw.rectangle([x, y, x+16, y+16], fill=(color[0]+40, color[1]+40, color[2]+40, 255))
        img.save(img_dir / f'large_tile_{i:03d}.png')
    
    # Create large UI elements (1024x1024) - 20 UI panels
    for i in range(20):
        img = Image.new('RGBA', (1024, 1024), (30, 30, 40, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([50, 50, 974, 974], radius=80, fill=(50, 50, 70, 255))
        draw.rounded_rectangle([100, 100, 924, 924], radius=40, fill=(40, 40, 60, 255))
        draw.text((400, 450), f'UI Panel {i}', fill=(200,200,200,255))
        img.save(img_dir / f'large_ui_{i:02d}.png')
    
    print('Large images created successfully')
    
except ImportError:
    print('PIL not available')

# Create large data files
# Extended lore and story (10 large JSON files)
for i in range(10):
    lore = {
        'chapter': i + 1,
        'title': f'Chapter {i+1}: The Ancient Prophecy',
        'content': ' '.join([f'Word{j}_chapter_{i}_sentence_{k}.' for j in range(100) for k in range(50)]),
        'characters': [f'Character_{i}_{j}' for j in range(20)],
        'locations': [f'Location_{i}_{j}' for j in range(15)],
        'items': [f'Item_{i}_{j}' for j in range(30)],
        'metadata': {'version': '1.0', 'created': '2025-01-01', 'author': 'Seven RPG Team'}
    }
    (data_dir / f'lore_chapter_{i+1}.json').write_text(json.dumps(lore, ensure_ascii=False, indent=2), encoding='utf-8')

# Create large skill trees (5 files)
for i in range(5):
    skill_tree = {
        'id': f'skill_tree_{i}',
        'name': f'Skill Tree {i+1}',
        'skills': {f'skill_{i}_{j}': {
            'name': f'Skill {j}',
            'description': ' '.join([f'desc_word_{k}' for k in range(200)]),
            'prerequisites': [f'skill_{i}_{max(0,j-1)}'],
            'effects': {'stat': 'strength', 'value': j * 5}
        } for j in range(50)},
        'nodes': [f'node_{i}_{j}' for j in range(100)]
    }
    (data_dir / f'skill_tree_{i+1}.json').write_text(json.dumps(skill_tree, ensure_ascii=False, indent=2), encoding='utf-8')

# Create large world generation parameters
world_gen = {
    'seed': 123456789,
    'size': 10000,
    'biomes': {f'biome_{i}': {
        'name': f'Biome {i}',
        'description': ' '.join([f'biome_word_{j}' for j in range(500)]),
        'resources': [f'resource_{i}_{j}' for j in range(50)],
        'creatures': [f'creature_{i}_{j}' for j in range(30)],
        'weather_patterns': [f'weather_{j}' for j in range(20)]
    } for i in range(20)},
    'generation_rules': {'rule_' + str(i): {'condition': f'if x > {i}', 'action': f'spawn_{i}'} for i in range(100)}
}
(data_dir / 'world_generation_full.json').write_text(json.dumps(world_gen, ensure_ascii=False, indent=2), encoding='utf-8')

print('Large data files created')
for f in data_dir.rglob('*.json'):
    print(f'  {f.name}: {f.stat().st_size / 1024:.1f} KB')