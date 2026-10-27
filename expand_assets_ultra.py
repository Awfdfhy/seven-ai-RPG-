import os, random, json
from pathlib import Path

assets_dir = Path('android-app/www/assets')
img_dir = assets_dir / 'images'
data_dir = assets_dir / 'data'
img_dir.mkdir(parents=True, exist_ok=True)
data_dir.mkdir(parents=True, exist_ok=True)

try:
    from PIL import Image, ImageDraw, ImageFont
    
    # Create ultra HD backgrounds (3840x2160) - 10 images
    for i in range(10):
        img = Image.new('RGBA', (3840, 2160), (0, 0, 0, 255))
        draw = ImageDraw.Draw(img)
        for y in range(2160):
            r = int(10 + (y / 2160) * 50)
            g = int(5 + (y / 2160) * 40)
            b = int(20 + (y / 2160) * 60)
            draw.line([(0, y), (3840, y)], fill=(r, g, b, 255))
        for _ in range(500):
            x = random.randint(0, 3840)
            y = random.randint(0, 2160)
            size = random.randint(20, 200)
            draw.ellipse([x, y, x+size, y+size], fill=(255, 255, 200, 80))
        draw.text((200, 200), f'Region {i} Ultra HD Background', fill=(255,255,255,255))
        img.save(img_dir / f'ultrahd_bg_{i}.png')
    
    # Create massive sprite sheets (4096x4096) - 5 sheets
    for i in range(5):
        img = Image.new('RGBA', (4096, 4096), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for row in range(16):
            for col in range(16):
                x = col * 256
                y = row * 256
                color = (random.randint(50,200), random.randint(50,200), random.randint(50,200))
                draw.rectangle([x+10, y+10, x+246, y+246], fill=color + (200,))
                draw.text((x+80, y+110), f'S{i}R{row}C{col}', fill=(255,255,255,255))
        img.save(img_dir / f'mega_spritesheet_{i}.png')
    
    # Create large texture atlases (2048x2048) - 10 atlases
    for i in range(10):
        img = Image.new('RGBA', (2048, 2048), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for row in range(8):
            for col in range(8):
                x = col * 256
                y = row * 256
                color = (random.randint(30,100), random.randint(30,100), random.randint(30,100))
                draw.rectangle([x, y, x+256, y+256], fill=color + (255,))
                for px in range(0, 256, 16):
                    for py in range(0, 256, 16):
                        if (px + py) % 32 == 0:
                            draw.rectangle([x+px, y+py, x+px+8, y+py+8], fill=(color[0]+30, color[1]+30, color[2]+30, 255))
        img.save(img_dir / f'texture_atlas_{i}.png')
    
    # Create large item icons (512x512) - 100 icons
    for i in range(100):
        img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        categories = ['weapon', 'armor', 'accessory', 'consumable', 'material', 'quest']
        cat = categories[i % len(categories)]
        cat_colors = {'weapon': (200,100,100), 'armor': (100,100,200), 'accessory': (200,200,100),
                     'consumable': (100,200,100), 'material': (150,150,150), 'quest': (200,100,200)}
        color = cat_colors[cat]
        draw.rounded_rectangle([40, 40, 472, 472], radius=80, fill=color + (220,))
        draw.text((160, 220), f'Item {i}', fill=(255,255,255,255))
        img.save(img_dir / f'xl_item_{i:03d}.png')
    
    print('Ultra large images created successfully')
    
except ImportError:
    print('PIL not available')

# Create massive data files
# Extended dialogue trees (10 files)
for i in range(10):
    dialogue_tree = {
        'npc_id': f'dialogue_tree_{i}',
        'name': f'Dialogue Tree {i+1}',
        'nodes': {f'node_{i}_{j}': {
            'text': ' '.join([f'dialogue_word_{k}' for k in range(300)]),
            'choices': [
                {'text': f'Choice {c}', 'next_node': f'node_{i}_{j+1}', 'condition': f'stat_{c} > 10'}
                for c in range(5)
            ]
        } for j in range(100)},
        'total_nodes': 100
    }
    (data_dir / f'dialogue_tree_{i+1}.json').write_text(json.dumps(dialogue_tree, ensure_ascii=False, indent=2), encoding='utf-8')

# Create large crafting recipes (5 files)
for i in range(5):
    recipes = {
        'category': ['weapon', 'armor', 'potion', 'enchantment', 'building'][i],
        'recipes': {f'recipe_{i}_{j}': {
            'name': f'Recipe {j}',
            'description': ' '.join([f'recipe_word_{k}' for k in range(400)]),
            'ingredients': [f'ingredient_{i}_{j}_{k}' for k in range(10)],
            'result': f'result_{i}_{j}',
            'difficulty': j % 5 + 1,
            'required_skill': f'skill_{j % 20}',
            'required_skill_level': (j % 50) + 1
        } for j in range(200)}
    }
    (data_dir / f'crafting_recipes_{i+1}.json').write_text(json.dumps(recipes, ensure_ascii=False, indent=2), encoding='utf-8')

# Create large enemy configurations (5 files)
for i in range(5):
    enemies = {
        'zone': i + 1,
        'enemies': {f'enemy_{i}_{j}': {
            'name': f'Enemy {j}',
            'description': ' '.join([f'enemy_desc_word_{k}' for k in range(250)]),
            'stats': {'hp': (j+1)*100, 'mp': (j+1)*50, 'attack': (j+1)*10, 'defense': (j+1)*5},
            'skills': [f'skill_{j}_{k}' for k in range(10)],
            'loot_table': [f'loot_{i}_{j}_{k}' for k in range(15)],
            'ai_pattern': ['aggressive', 'defensive', 'tactical', 'berserker', 'support'][j % 5],
            'spawn_conditions': {'time': 'night', 'weather': 'rain', 'player_level': (j % 30) + 1}
        } for j in range(200)}
    }
    (data_dir / f'enemy_config_{i+1}.json').write_text(json.dumps(enemies, ensure_ascii=False, indent=2), encoding='utf-8')

print('Massive data files created')
for f in data_dir.rglob('*.json'):
    print(f'  {f.name}: {f.stat().st_size / 1024:.1f} KB')