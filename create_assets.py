import os, json
from pathlib import Path

assets_dir = Path('android-app/www/assets')
assets_dir.mkdir(parents=True, exist_ok=True)

# 1. Extended Character Data
char_data = {
    'classes': [
        {'id': 'warrior', 'name': 'Warrior', 'name_kr': '전사', 'name_ar': 'محارب', 'primary_stat': 'strength', 'skills': ['slash', 'block', 'charge']},
        {'id': 'mage', 'name': 'Mage', 'name_kr': '마법사', 'name_ar': 'ساحر', 'primary_stat': 'intelligence', 'skills': ['fireball', 'ice_shard', 'arcane_missile']},
        {'id': 'rogue', 'name': 'Rogue', 'name_kr': '도적', 'name_ar': 'لص', 'primary_stat': 'dexterity', 'skills': ['backstab', 'evasion', 'poison_blade']},
        {'id': 'cleric', 'name': 'Cleric', 'name_kr': '성직자', 'name_ar': 'كاهن', 'primary_stat': 'wisdom', 'skills': ['heal', 'bless', 'turn_undead']},
        {'id': 'ranger', 'name': 'Ranger', 'name_kr': '레인저', 'name_ar': 'حارس', 'primary_stat': 'dexterity', 'skills': ['aimed_shot', 'trap', 'animal_companion']},
        {'id': 'paladin', 'name': 'Paladin', 'name_kr': '성기사', 'name_ar': 'فارس مقدس', 'primary_stat': 'strength', 'skills': ['holy_strike', 'divine_shield', 'lay_on_hands']},
        {'id': 'warlock', 'name': 'Warlock', 'name_kr': '흑마법사', 'name_ar': 'ساحر مظلم', 'primary_stat': 'charisma', 'skills': ['eldritch_blast', 'curse', 'demon_pact']},
        {'id': 'monk', 'name': 'Monk', 'name_kr': '수도사', 'name_ar': 'راهب', 'primary_stat': 'dexterity', 'skills': ['flurry', 'meditate', 'ki_strike']}
    ],
    'backgrounds': [
        {'id': 'noble', 'name': 'Noble', 'name_kr': '귀족', 'name_ar': 'نبيل', 'bonus': 'persuasion'},
        {'id': 'soldier', 'name': 'Soldier', 'name_kr': '병사', 'name_ar': 'جندي', 'bonus': 'athletics'},
        {'id': 'scholar', 'name': 'Scholar', 'name_kr': '학자', 'name_ar': 'عالم', 'bonus': 'history'},
        {'id': 'criminal', 'name': 'Criminal', 'name_kr': '범죄자', 'name_ar': 'مجرم', 'bonus': 'stealth'},
        {'id': 'artisan', 'name': 'Artisan', 'name_kr': '장인', 'name_ar': 'حرفي', 'bonus': 'crafting'},
        {'id': 'hermit', 'name': 'Hermit', 'name_kr': '은둔자', 'name_ar': 'منعزل', 'bonus': 'insight'}
    ]
}
(assets_dir / 'data' / 'character_database.json').write_text(json.dumps(char_data, ensure_ascii=False, indent=2), encoding='utf-8')

# 2. Extended Items Database
categories = ['weapon', 'armor', 'accessory', 'consumable', 'material', 'quest']
rarities = ['common', 'uncommon', 'rare', 'epic', 'legendary']
items = []
for i in range(500):
    items.append({
        'id': f'item_{i:04d}',
        'name': f'Item {i}',
        'name_kr': f'아이템 {i}',
        'name_ar': f'عنصر {i}',
        'category': categories[i % len(categories)],
        'rarity': rarities[i % len(rarities)],
        'value': (i + 1) * 10,
        'weight': (i % 50) + 1,
        'description': f'Description for item {i}',
        'effects': {'stat': f'stat_{i % 6}', 'value': (i % 20) + 1}
    })
(assets_dir / 'data' / 'items_database.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

# 3. Extended Quests Database
quests = []
for i in range(200):
    quests.append({
        'id': f'quest_{i:04d}',
        'title': f'Quest {i}: The Adventure',
        'title_kr': f'퀘스트 {i}: 모험',
        'title_ar': f'مهمة {i}: المغامرة',
        'description': f'Detailed description for quest {i} with multiple objectives and branching paths.',
        'type': ['main', 'side', 'daily', 'weekly', 'event'][i % 5],
        'level_req': (i % 50) + 1,
        'rewards': {'xp': (i + 1) * 50, 'gold': (i + 1) * 10, 'items': [f'item_{(i*3) % 500:04d}']},
        'objectives': [
            {'id': f'obj_{i}_1', 'type': 'kill', 'target': f'enemy_{(i*2) % 50}', 'count': (i % 10) + 1},
            {'id': f'obj_{i}_2', 'type': 'collect', 'target': f'item_{(i*5) % 500:04d}', 'count': (i % 5) + 1},
            {'id': f'obj_{i}_3', 'type': 'explore', 'target': f'location_{(i*7) % 100}', 'count': 1}
        ]
    })
(assets_dir / 'data' / 'quests_database.json').write_text(json.dumps(quests, ensure_ascii=False, indent=2), encoding='utf-8')

# 4. World Map Data
world_map = {
    'regions': [
        {'id': f'region_{i}', 'name': f'Region {i}', 'name_kr': f'지역 {i}', 'name_ar': f'منطقة {i}', 'biome': ['forest', 'desert', 'mountain', 'swamp', 'plains', 'tundra', 'jungle', 'volcanic'][i % 8], 'level_range': [i*5+1, i*5+10], 'locations': [f'loc_{i}_{j}' for j in range(10)]} for i in range(20)
    ],
    'locations': []
}
for i in range(200):
    world_map['locations'].append({
        'id': f'loc_{i//10}_{i%10}',
        'name': f'Location {i}',
        'name_kr': f'위치 {i}',
        'name_ar': f'موقع {i}',
        'type': ['town', 'dungeon', 'ruins', 'cave', 'tower', 'shrine', 'camp', 'landmark'][i % 8],
        'danger_level': (i % 10) + 1,
        'services': ['shop', 'inn', 'quest_giver', 'crafting', 'trainer'][i % 5::2]
    })
(assets_dir / 'data' / 'world_map.json').write_text(json.dumps(world_map, ensure_ascii=False, indent=2), encoding='utf-8')

# 5. NPC Dialogue Data
npcs = []
for i in range(300):
    npcs.append({
        'id': f'npc_{i:04d}',
        'name': f'NPC {i}',
        'name_kr': f'NPC {i}',
        'name_ar': f'شخصية {i}',
        'role': ['merchant', 'quest_giver', 'trainer', 'guard', 'villager', 'noble', 'scholar'][i % 7],
        'dialogue': {
            'greeting': [f'Hello traveler!', f'Welcome to our town.', f'Greetings, adventurer.'][i % 3],
            'farewell': [f'Safe travels!', f'Come back soon.', f'May the gods protect you.'][i % 3],
            'shop': ['Take a look at my wares.', f'Special prices for you.', f'Quality goods, fair prices.'][i % 3] if i % 7 == 0 else None
        },
        'personality': {'friendliness': (i % 100) + 1, 'honesty': (i % 100) + 1, 'bravery': (i % 100) + 1}
    })
(assets_dir / 'data' / 'npcs_database.json').write_text(json.dumps(npcs, ensure_ascii=False, indent=2), encoding='utf-8')

# 6. Localization Files
locales = ['en', 'ko', 'ar']
base_strings = {
    'game_title': 'Seven RPG', 'new_game': 'New Game', 'continue': 'Continue', 'options': 'Options',
    'credits': 'Credits', 'quit': 'Quit', 'save': 'Save Game', 'load': 'Load Game',
    'inventory': 'Inventory', 'character': 'Character', 'quests': 'Quests', 'map': 'World Map',
    'settings': 'Settings', 'audio': 'Audio', 'video': 'Video', 'gameplay': 'Gameplay',
    'accessibility': 'Accessibility', 'language': 'Language', 'difficulty': 'Difficulty',
    'easy': 'Easy', 'normal': 'Normal', 'hard': 'Hard', 'nightmare': 'Nightmare',
    'colorblind_off': 'Off', 'colorblind_protanopia': 'Protanopia', 'colorblind_deuteranopia': 'Deuteranopia',
    'colorblind_tritanopia': 'Tritanopia', 'colorblind_monochrome': 'Monochrome',
    'text_size_small': 'Small', 'text_size_normal': 'Normal', 'text_size_large': 'Large', 'text_size_xlarge': 'Extra Large',
    'high_contrast': 'High Contrast', 'simplified_controls': 'Simplified Controls',
    'attack': 'Attack', 'defend': 'Defend', 'skill': 'Skill', 'item': 'Item', 'flee': 'Flee',
    'level_up': 'Level Up!', 'experience': 'Experience', 'gold': 'Gold', 'health': 'Health', 'mana': 'Mana',
    'strength': 'Strength', 'dexterity': 'Dexterity', 'intelligence': 'Intelligence', 'wisdom': 'Wisdom',
    'constitution': 'Constitution', 'charisma': 'Charisma'
}
translations = {
    'ko': {
        'game_title': '세븐 RPG', 'new_game': '새 게임', 'continue': '이어하기', 'options': '옵션',
        'credits': '크레딧', 'quit': '종료', 'save': '저장', 'load': '불러오기',
        'inventory': '인벤토리', 'character': '캐릭터', 'quests': '퀘스트', 'map': '세계 지도',
        'settings': '설정', 'audio': '오디오', 'video': '비디오', 'gameplay': '게임플레이',
        'accessibility': '접근성', 'language': '언어', 'difficulty': '난이도',
        'easy': '쉬움', 'normal': '보통', 'hard': '어려움', 'nightmare': '악몽',
        'colorblind_off': '끔', 'colorblind_protanopia': '적색맹', 'colorblind_deuteranopia': '녹색맹',
        'colorblind_tritanopia': '청색맹', 'colorblind_monochrome': '흑백',
        'text_size_small': '작게', 'text_size_normal': '보통', 'text_size_large': '크게', 'text_size_xlarge': '매우 크게',
        'high_contrast': '높은 대비', 'simplified_controls': '간단 조작',
        'attack': '공격', 'defend': '방어', 'skill': '스킬', 'item': '아이템', 'flee': '도망',
        'level_up': '레벨 업!', 'experience': '경험치', 'gold': '골드', 'health': '체력', 'mana': '마나',
        'strength': '힘', 'dexterity': '민첩', 'intelligence': '지능', 'wisdom': '지혜',
        'constitution': '체질', 'charisma': '매력'
    },
    'ar': {
        'game_title': 'سبعة آر بي جي', 'new_game': 'لعبة جديدة', 'continue': 'متابعة', 'options': 'خيارات',
        'credits': 'الشكر', 'quit': 'خروج', 'save': 'حفظ اللعبة', 'load': 'تحميل اللعبة',
        'inventory': 'المخزون', 'character': 'الشخصية', 'quests': 'المهام', 'map': 'خريطة العالم',
        'settings': 'الإعدادات', 'audio': 'الصوت', 'video': 'الفيديو', 'gameplay': 'اللعب',
        'accessibility': 'إمكانية الوصول', 'language': 'اللغة', 'difficulty': 'الصعوبة',
        'easy': 'سهل', 'normal': 'عادي', 'hard': 'صعب', 'nightmare': 'كابوس',
        'colorblind_off': 'إيقاف', 'colorblind_protanopia': 'عمى الأحمر', 'colorblind_deuteranopia': 'عمى الأخضر',
        'colorblind_tritanopia': 'عمى الأزرق', 'colorblind_monochrome': 'أحادي اللون',
        'text_size_small': 'صغير', 'text_size_normal': 'عادي', 'text_size_large': 'كبير', 'text_size_xlarge': 'كبير جداً',
        'high_contrast': 'تباين عالي', 'simplified_controls': 'تحكم مبسط',
        'attack': 'هجوم', 'defend': 'دفاع', 'skill': 'مهارة', 'item': 'عنصر', 'flee': 'هروب',
        'level_up': 'ترقية المستوى!', 'experience': 'الخبرة', 'gold': 'ذهب', 'health': 'الصحة', 'mana': 'المانا',
        'strength': 'القوة', 'dexterity': 'الرشاقة', 'intelligence': 'الذكاء', 'wisdom': 'الحكمة',
        'constitution': 'الدستور', 'charisma': 'الكاريزما'
    }
}
for locale in locales:
    data = {}
    for key, val in base_strings.items():
        if locale == 'en':
            data[key] = val
        else:
            data[key] = translations.get(locale, {}).get(key, val)
    (assets_dir / 'data' / f'locale_{locale}.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

print('Data files created')
for f in assets_dir.rglob('*.json'):
    print(f'  {f.relative_to(assets_dir)}: {f.stat().st_size / 1024:.1f} KB')