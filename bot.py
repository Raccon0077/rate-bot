import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import random
import re
import json
import os
import math

# Токен группы ВК
VK_TOKEN = "vk1.a.pWAMTUhJkodcMkUFpCa-UMg_6DKXwr6ISV863itpGw410z1RVSyawnce0r8wMMho0eD5rtIVnrITM22tQbnuqGtnJBZfH5FLopBeT33UG0AUbJI_cEJVbcJEAvOs34dt3PfAA0yiL0sjgabDA88ll9GRCB2nyxiywcI5286nSS-Db2Rn5AAzgp3nkzXfWzkLc4Xf-_vPgUu7pMVJc490Vw"

# ID группы
GROUP_ID = 239699656

# ID админов
EKATERINA_ID = 212887447
VELES_ID = 816395698
ADMIN_IDS = [EKATERINA_ID, VELES_ID]

# Файл для хранения профилей
PROFILES_FILE = "profiles.json"


class VKBot:
    def __init__(self, token, group_id):
        self.token = token
        self.group_id = group_id
        self.vk_session = vk_api.VkApi(token=token)
        self.vk = self.vk_session.get_api()
        self.longpoll = VkBotLongPoll(self.vk_session, group_id)
        self.active_chats = {2000000006, 2000000004}
        self.profiles = self.load_profiles()
        self.last_forwarded = {}
        
        self._init_profiles()
        self.save_profiles()
        print(f"🔑 Бот запущен!")
        print(f"👑 Админы: Екатерина (ID: {EKATERINA_ID}), Велес (ID: {VELES_ID})")
        print(f"📋 Загружено профилей: {len(self.profiles)}")
        print(f"⚖️ Все игроки бросают кости с одинаковыми шансами!")
        print(f"📩 Изменения профилей дублируются в ЛС Екатерине")

    def _init_profiles(self):
        profiles = {
            "202343829": {
                "name": "Финд",
                "race": "Демон",
                "class": "Убийца",
                "hp": 100,
                "armor": 0,
                "attack": 0,
                "stats": {"stamina": 10, "strength": 10, "agility": 15, "charisma": 10, "intellect": 5},
                "skills": {"active": ["Рывок"], "passive": ["Уклонение"]}
            },
            "706455479": {
                "name": "Малкор",
                "race": "Разумная нежить",
                "class": "Призыватель",
                "hp": 50,
                "armor": 0,
                "attack": 0,
                "stats": {"stamina": 5, "strength": 5, "agility": 5, "charisma": 15, "intellect": 20},
                "skills": {"active": ["Призыв"], "passive": ["Подчинение"]}
            },
            "536755029": {
                "name": "Деркитус",
                "race": "Человек",
                "class": "Танк",
                "hp": 200,
                "armor": 0,
                "attack": 0,
                "stats": {"stamina": 20, "strength": 20, "agility": 5, "charisma": 2, "intellect": 3},
                "skills": {"active": ["Провокация"], "passive": ["Стойкость"]}
            },
            "281721241": {
                "name": "Эксель",
                "race": "Эльф",
                "class": "Хилер",
                "hp": 100,
                "armor": 0,
                "attack": 0,
                "stats": {"stamina": 10, "strength": 5, "agility": 10, "charisma": 10, "intellect": 15},
                "skills": {"active": ["Длань"], "passive": ["Восстановление"]}
            },
            "675074277": {
                "name": "Грэм",
                "race": "Нежить",
                "class": "Убийца",
                "hp": 50,
                "armor": 0,
                "attack": 0,
                "stats": {"stamina": 5, "strength": 10, "agility": 15, "charisma": 10, "intellect": 10},
                "skills": {"active": ["Рывок"], "passive": ["Уклонение"]}
            }
        }
        
        for user_id, profile in profiles.items():
            if user_id not in self.profiles:
                self.profiles[user_id] = profile
                print(f"✅ Добавлен профиль: {profile['name']} (ID: {user_id})")

    def load_profiles(self):
        if os.path.exists(PROFILES_FILE):
            try:
                with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    print(f"📂 Загружено {len(data)} профилей из файла")
                    return data
            except Exception as e:
                print(f"⚠️ Ошибка загрузки профилей: {e}")
                return {}
        return {}

    def save_profiles(self):
        try:
            with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.profiles, f, ensure_ascii=False, indent=2)
            print(f"💾 Сохранено {len(self.profiles)} профилей в файл")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения профилей: {e}")
            return False

    def send_profile_to_admin(self, user_id, profile_data, action=""):
        """Отправляет профиль в ЛС Екатерине при изменениях"""
        try:
            # Формируем сообщение
            stats = profile_data['stats']
            modifiers = {
                'stamina': self.get_modifier(stats['stamina']),
                'strength': self.get_modifier(stats['strength']),
                'agility': self.get_modifier(stats['agility']),
                'charisma': self.get_modifier(stats['charisma']),
                'intellect': self.get_modifier(stats['intellect'])
            }
            
            active_skills = [self.clean_skill_name(s) for s in profile_data['skills']['active']]
            passive_skills = [self.clean_skill_name(s) for s in profile_data['skills']['passive']]
            
            msg = f"📩 **Обновление профиля** {action}\n\n"
            msg += f"📋 Имя: {profile_data['name']}\n"
            msg += f"👤 Раса: {profile_data['race']}\n"
            msg += f"⚙ Класс: {profile_data['class']}\n"
            msg += f"💚 ХП: {profile_data['hp']}   🛡 Броня: {profile_data['armor']}   🗡 Атака: {profile_data['attack']}\n"
            msg += f"🦴 Стойкость: {stats['stamina']} ({modifiers['stamina']})\n"
            msg += f"✊ Сила: {stats['strength']} ({modifiers['strength']})\n"
            msg += f"💅 Ловкость: {stats['agility']} ({modifiers['agility']})\n"
            msg += f"💗 Харизма: {stats['charisma']} ({modifiers['charisma']})\n"
            msg += f"🧠 Интеллект: {stats['intellect']} ({modifiers['intellect']})\n"
            msg += f"\n📜 Навыки\n"
            msg += f"⚔ Активные: {', '.join(active_skills)}\n"
            msg += f"⚒ Пассивные: {', '.join(passive_skills)}"
            
            # Отправляем Екатерине в ЛС
            self.vk.messages.send(
                user_id=EKATERINA_ID,
                message=msg,
                random_id=random.randint(1, 2 ** 31)
            )
        except Exception as e:
            print(f"⚠️ Не удалось отправить профиль в ЛС: {e}")

    def get_keyboard(self):
        keyboard = VkKeyboard(one_time=False, inline=False)
        keyboard.add_button('🎲 d6', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('🎲 d8', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('🎲 d10', color=VkKeyboardColor.PRIMARY)
        keyboard.add_button('🎲 d12', color=VkKeyboardColor.PRIMARY)
        keyboard.add_line()
        keyboard.add_button('🎲 d20', color=VkKeyboardColor.POSITIVE)
        keyboard.add_button('👤 Мой профиль', color=VkKeyboardColor.SECONDARY)
        return keyboard

    def get_clear_keyboard(self):
        keyboard = VkKeyboard(one_time=True, inline=False)
        keyboard.add_button('🔄 Убрать кнопки', color=VkKeyboardColor.SECONDARY)
        return keyboard

    def get_modifier(self, stat):
        return math.ceil(stat / 5)

    def calculate_hp(self, stamina):
        return stamina * 10

    def create_profile(self, user_id, user_name):
        stamina = 10
        profile = {
            'name': user_name,
            'race': 'Человек',
            'class': 'Воин',
            'hp': self.calculate_hp(stamina),
            'armor': 0,
            'attack': 10,
            'stats': {
                'stamina': stamina,
                'strength': 10,
                'agility': 10,
                'charisma': 10,
                'intellect': 10
            },
            'skills': {
                'active': ['Рывок'],
                'passive': ['Уклонение']
            }
        }
        self.profiles[str(user_id)] = profile
        self.save_profiles()
        # Отправляем созданный профиль админу
        self.send_profile_to_admin(user_id, profile, "(создан)")
        return self.profiles[str(user_id)]

    def get_profile(self, user_id):
        user_id_str = str(user_id)
        if user_id_str not in self.profiles:
            return None
        return self.profiles[user_id_str]

    def get_or_create_profile(self, user_id):
        user_id_str = str(user_id)
        if user_id_str not in self.profiles:
            user_name = self.get_user_name(user_id)
            return self.create_profile(user_id, user_name)
        return self.profiles[user_id_str]

    def find_user_by_name(self, name):
        if not name:
            return None
        name_lower = name.lower().strip()
        
        for user_id, profile in self.profiles.items():
            profile_name = profile['name'].lower().strip()
            profile_name_clean = re.sub(r'[👑]', '', profile_name).strip()
            
            if profile_name == name_lower or profile_name_clean == name_lower:
                return user_id
            if name_lower in profile_name_clean or profile_name_clean in name_lower:
                return user_id
        return None

    def clean_skill_name(self, skill_name):
        if not skill_name:
            return skill_name
        if '+' in skill_name:
            skill_name = skill_name.split('+')[0].strip()
        return skill_name

    def format_profile(self, user_id):
        profile = self.get_profile(user_id)
        if not profile:
            return None
        
        stats = profile['stats']
        modifiers = {
            'stamina': self.get_modifier(stats['stamina']),
            'strength': self.get_modifier(stats['strength']),
            'agility': self.get_modifier(stats['agility']),
            'charisma': self.get_modifier(stats['charisma']),
            'intellect': self.get_modifier(stats['intellect'])
        }
        
        active_skills = [self.clean_skill_name(s) for s in profile['skills']['active']]
        passive_skills = [self.clean_skill_name(s) for s in profile['skills']['passive']]
        
        msg = f"📋 Имя: {profile['name']}\n"
        msg += f"👤 Раса: {profile['race']}\n"
        msg += f"⚙ Класс: {profile['class']}\n"
        msg += f"💚 ХП: {profile['hp']}   🛡 Броня: {profile['armor']}   🗡 Атака: {profile['attack']}\n"
        msg += f"🦴 Стойкость: {stats['stamina']} ({modifiers['stamina']})\n"
        msg += f"✊ Сила: {stats['strength']} ({modifiers['strength']})\n"
        msg += f"💅 Ловкость: {stats['agility']} ({modifiers['agility']})\n"
        msg += f"💗 Харизма: {stats['charisma']} ({modifiers['charisma']})\n"
        msg += f"🧠 Интеллект: {stats['intellect']} ({modifiers['intellect']})\n"
        msg += f"\n📜 Навыки\n"
        msg += f"⚔ Активные: {', '.join(active_skills)}\n"
        msg += f"⚒ Пассивные: {', '.join(passive_skills)}"
        return msg

    def get_all_players(self):
        players = []
        for user_id, profile in self.profiles.items():
            if int(user_id) not in ADMIN_IDS:
                players.append(profile['name'])
        return sorted(players)

    def parse_profile_from_text(self, text):
        profile_data = {
            'name': None,
            'race': None,
            'class': None,
            'hp': None,
            'armor': None,
            'attack': None,
            'stats': {
                'stamina': None,
                'strength': None,
                'agility': None,
                'charisma': None,
                'intellect': None
            },
            'skills': {
                'active': [],
                'passive': []
            }
        }
        
        clean_text = re.sub(r'игрок\+', '', text, flags=re.IGNORECASE)
        clean_text = re.sub(r'\+проф', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'\+профиль', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'кости\+', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r'кости-', '', clean_text, flags=re.IGNORECASE)
        
        patterns = {
            'name': r'(?:Имя|имя)[:\-]?\s*([^\n]+)',
            'race': r'(?:Раса|раса)[:\-]?\s*([^\n]+)',
            'class': r'(?:Класс|класс)[:\-]?\s*([^\n]+)',
            'hp': r'(?:ХП|хп)[:\-]?\s*(\d+)',
            'armor': r'(?:Броня|броня)[:\-]?\s*(\d+)',
            'attack': r'(?:Атака|атака)[:\-]?\s*(\d+)',
            'stamina': r'(?:Стойкость|стойкость)[:\-]?\s*(\d+)',
            'strength': r'(?:Сила|сила)[:\-]?\s*(\d+)',
            'agility': r'(?:Ловкость|ловкость)[:\-]?\s*(\d+)',
            'charisma': r'(?:Харизма|харизма)[:\-]?\s*(\d+)',
            'intellect': r'(?:Интеллект|интеллект)[:\-]?\s*(\d+)',
            'active': r'(?:Активные|активные)[:\-]?\s*([^\n]+)',
            'passive': r'(?:Пассивные|пассивные)[:\-]?\s*([^\n]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if key == 'name':
                    profile_data['name'] = value
                elif key == 'race':
                    profile_data['race'] = value
                elif key == 'class':
                    profile_data['class'] = value
                elif key == 'hp':
                    try:
                        profile_data['hp'] = int(value)
                    except:
                        pass
                elif key == 'armor':
                    try:
                        profile_data['armor'] = int(value)
                    except:
                        pass
                elif key == 'attack':
                    try:
                        profile_data['attack'] = int(value)
                    except:
                        pass
                elif key == 'stamina':
                    try:
                        profile_data['stats']['stamina'] = int(value)
                    except:
                        pass
                elif key == 'strength':
                    try:
                        profile_data['stats']['strength'] = int(value)
                    except:
                        pass
                elif key == 'agility':
                    try:
                        profile_data['stats']['agility'] = int(value)
                    except:
                        pass
                elif key == 'charisma':
                    try:
                        profile_data['stats']['charisma'] = int(value)
                    except:
                        pass
                elif key == 'intellect':
                    try:
                        profile_data['stats']['intellect'] = int(value)
                    except:
                        pass
                elif key == 'active':
                    skills = [s.strip() for s in value.split(',') if s.strip()]
                    profile_data['skills']['active'] = skills
                elif key == 'passive':
                    skills = [s.strip() for s in value.split(',') if s.strip()]
                    profile_data['skills']['passive'] = skills
        
        return profile_data

    def update_profile_from_data(self, user_id, profile_data):
        profile = self.get_or_create_profile(user_id)
        
        if profile_data['name']:
            profile['name'] = profile_data['name']
        if profile_data['race']:
            profile['race'] = profile_data['race']
        if profile_data['class']:
            profile['class'] = profile_data['class']
        if profile_data['hp'] is not None:
            profile['hp'] = profile_data['hp']
        if profile_data['armor'] is not None:
            profile['armor'] = profile_data['armor']
        if profile_data['attack'] is not None:
            profile['attack'] = profile_data['attack']
        
        for stat, value in profile_data['stats'].items():
            if value is not None:
                profile['stats'][stat] = max(1, value)
        
        if profile_data['skills']['active']:
            profile['skills']['active'] = profile_data['skills']['active']
        if profile_data['skills']['passive']:
            profile['skills']['passive'] = profile_data['skills']['passive']
        
        stamina = profile['stats']['stamina']
        profile['hp'] = self.calculate_hp(stamina)
        
        self.save_profiles()
        # Отправляем обновлённый профиль админу
        self.send_profile_to_admin(user_id, profile, "(обновлён)")
        return profile

    def delete_profile(self, user_id):
        user_id_str = str(user_id)
        if user_id_str in self.profiles:
            del self.profiles[user_id_str]
            self.save_profiles()
            return True
        return False

    def roll_dice(self, sides, user_id):
        weights = [sides - i + 1 for i in range(sides)]
        return random.choices(range(1, sides + 1), weights=weights, k=1)[0]

    def send_message(self, peer_id, message, keyboard=None):
        try:
            params = {
                'peer_id': peer_id,
                'message': message,
                'random_id': random.randint(1, 2 ** 31)
            }
            if keyboard:
                params['keyboard'] = keyboard.get_keyboard()
            self.vk.messages.send(**params)
        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def get_user_name(self, user_id):
        try:
            user = self.vk.users.get(user_ids=user_id)[0]
            name = user['first_name']
            if user_id in ADMIN_IDS:
                name = f"👑 {name}"
            return name
        except:
            return "Пользователь"

    def clean_text(self, text):
        if not text:
            return ""
        text = re.sub(r'\[club\d+\|@club\d+\]\s*', '', text)
        text = re.sub(r'@club\d+\s*', '', text)
        text = text.replace('🎲', '').replace('🔄', '').replace('👤', '')
        return text.strip().lower()

    def update_hp_from_stamina(self, profile):
        stamina = profile['stats']['stamina']
        profile['hp'] = self.calculate_hp(stamina)
        return profile

    def handle_admin_command(self, text, peer_id, user_id):
        if user_id not in ADMIN_IDS:
            return False
        
        clean_text = self.clean_text(text)
        if clean_text in ['мой профиль', 'профиль', '+проф', '+профиль']:
            return False
        
        print(f"🔧 Админская команда: {text}")
        
        parts = text.split()
        if len(parts) < 1:
            return False
        
        command = parts[0].lower()
        
        # ===== ИЗМЕНЕНИЕ БРОНИ: броня+5 Имя или броня-5 Имя =====
        if command.startswith('броня'):
            change_str = command.replace('броня', '')
            try:
                change = int(change_str) if change_str else 0
            except:
                change = 0
            
            if change == 0:
                match = re.search(r'броня([+-]?\d+)', command)
                if match:
                    change = int(match.group(1))
            
            if change != 0:
                print(f"   Изменение: броня {change:+}")
                
                target_name = None
                for part in parts[1:]:
                    if self.find_user_by_name(part):
                        target_name = part
                        break
                
                if target_name:
                    target_id = self.find_user_by_name(target_name)
                    if target_id:
                        profile = self.get_or_create_profile(int(target_id))
                        old_value = profile['armor']
                        profile['armor'] = max(0, old_value + change)
                        self.save_profiles()
                        self.send_profile_to_admin(int(target_id), profile, f"(броня: {old_value} → {profile['armor']})")
                        self.send_message(
                            peer_id, 
                            f"✅ {profile['name']}: Броня изменена с {old_value} на {profile['armor']}", 
                            self.get_keyboard()
                        )
                        return True
                    else:
                        self.send_message(peer_id, f"❌ Пользователь '{target_name}' не найден", self.get_keyboard())
                        return True
                else:
                    profile = self.get_or_create_profile(user_id)
                    old_value = profile['armor']
                    profile['armor'] = max(0, old_value + change)
                    self.save_profiles()
                    self.send_profile_to_admin(user_id, profile, f"(броня: {old_value} → {profile['armor']})")
                    self.send_message(
                        peer_id, 
                        f"✅ Броня изменена с {old_value} на {profile['armor']}", 
                        self.get_keyboard()
                    )
                    return True
        
        # ===== ИЗМЕНЕНИЕ АТАКИ: атака+5 Имя или атака-5 Имя =====
        if command.startswith('атака'):
            change_str = command.replace('атака', '')
            try:
                change = int(change_str) if change_str else 0
            except:
                change = 0
            
            if change == 0:
                match = re.search(r'атака([+-]?\d+)', command)
                if match:
                    change = int(match.group(1))
            
            if change != 0:
                print(f"   Изменение: атака {change:+}")
                
                target_name = None
                for part in parts[1:]:
                    if self.find_user_by_name(part):
                        target_name = part
                        break
                
                if target_name:
                    target_id = self.find_user_by_name(target_name)
                    if target_id:
                        profile = self.get_or_create_profile(int(target_id))
                        old_value = profile['attack']
                        profile['attack'] = max(0, old_value + change)
                        self.save_profiles()
                        self.send_profile_to_admin(int(target_id), profile, f"(атака: {old_value} → {profile['attack']})")
                        self.send_message(
                            peer_id, 
                            f"✅ {profile['name']}: Атака изменена с {old_value} на {profile['attack']}", 
                            self.get_keyboard()
                        )
                        return True
                    else:
                        self.send_message(peer_id, f"❌ Пользователь '{target_name}' не найден", self.get_keyboard())
                        return True
                else:
                    profile = self.get_or_create_profile(user_id)
                    old_value = profile['attack']
                    profile['attack'] = max(0, old_value + change)
                    self.save_profiles()
                    self.send_profile_to_admin(user_id, profile, f"(атака: {old_value} → {profile['attack']})")
                    self.send_message(
                        peer_id, 
                        f"✅ Атака изменена с {old_value} на {profile['attack']}", 
                        self.get_keyboard()
                    )
                    return True
        
        # ===== ИЗМЕНЕНИЕ ХАРАКТЕРИСТИК =====
        stat_patterns = {
            r'^ст([+-]?\d+)$': 'stamina',
            r'^си([+-]?\d+)$': 'strength',
            r'^л([+-]?\d+)$': 'agility',
            r'^х([+-]?\d+)$': 'charisma',
            r'^и([+-]?\d+)$': 'intellect',
            r'^хп([+-]?\d+)$': 'hp'
        }
        
        for pattern, stat_name in stat_patterns.items():
            match = re.match(pattern, command)
            if match:
                change = int(match.group(1))
                if change == 0:
                    return False
                
                print(f"   Изменение: {stat_name} {change:+}")
                
                target_name = None
                if len(parts) > 1:
                    target_name = ' '.join(parts[1:])
                
                if target_name:
                    target_id = self.find_user_by_name(target_name)
                    if target_id:
                        profile = self.get_or_create_profile(int(target_id))
                        if stat_name == 'hp':
                            old_value = profile['hp']
                            profile['hp'] = max(1, old_value + change)
                            self.save_profiles()
                            self.send_profile_to_admin(int(target_id), profile, f"(ХП: {old_value} → {profile['hp']})")
                            self.send_message(
                                peer_id, 
                                f"✅ {profile['name']}: ХП изменено с {old_value} на {profile['hp']}", 
                                self.get_keyboard()
                            )
                            return True
                        else:
                            old_value = profile['stats'][stat_name]
                            profile['stats'][stat_name] = max(1, old_value + change)
                            if stat_name == 'stamina':
                                old_hp = profile['hp']
                                self.update_hp_from_stamina(profile)
                                hp_msg = f", HP: {old_hp} → {profile['hp']}"
                            else:
                                hp_msg = ""
                            self.save_profiles()
                            new_modifier = self.get_modifier(profile['stats'][stat_name])
                            self.send_profile_to_admin(
                                int(target_id), 
                                profile, 
                                f"({stat_name}: {old_value} → {profile['stats'][stat_name]}, мод: {new_modifier}){hp_msg}"
                            )
                            self.send_message(
                                peer_id, 
                                f"✅ {profile['name']}: {stat_name} изменена с {old_value} на {profile['stats'][stat_name]} (мод: {new_modifier}){hp_msg}", 
                                self.get_keyboard()
                            )
                            return True
                    else:
                        self.send_message(peer_id, f"❌ Пользователь '{target_name}' не найден", self.get_keyboard())
                        return True
                else:
                    profile = self.get_or_create_profile(user_id)
                    if stat_name == 'hp':
                        old_value = profile['hp']
                        profile['hp'] = max(1, old_value + change)
                        self.save_profiles()
                        self.send_profile_to_admin(user_id, profile, f"(ХП: {old_value} → {profile['hp']})")
                        self.send_message(
                            peer_id, 
                            f"✅ ХП изменено с {old_value} на {profile['hp']}", 
                            self.get_keyboard()
                        )
                        return True
                    else:
                        old_value = profile['stats'][stat_name]
                        profile['stats'][stat_name] = max(1, old_value + change)
                        if stat_name == 'stamina':
                            old_hp = profile['hp']
                            self.update_hp_from_stamina(profile)
                            hp_msg = f", HP: {old_hp} → {profile['hp']}"
                        else:
                            hp_msg = ""
                        self.save_profiles()
                        new_modifier = self.get_modifier(profile['stats'][stat_name])
                        self.send_profile_to_admin(
                            user_id, 
                            profile, 
                            f"({stat_name}: {old_value} → {profile['stats'][stat_name]}, мод: {new_modifier}){hp_msg}"
                        )
                        self.send_message(
                            peer_id, 
                            f"✅ {stat_name} изменена с {old_value} на {profile['stats'][stat_name]} (мод: {new_modifier}){hp_msg}", 
                            self.get_keyboard()
                        )
                        return True
        
        if command == 'активка':
            if len(parts) > 1:
                full_text = ' '.join(parts[1:])
                
                target_name = None
                skill_name = full_text
                
                words = full_text.split()
                if len(words) > 1:
                    potential_name = words[-1]
                    if self.find_user_by_name(potential_name):
                        target_name = potential_name
                        skill_name = ' '.join(words[:-1])
                
                if skill_name.endswith('+'):
                    skill_name = skill_name[:-1].strip()
                
                if target_name:
                    target_id = self.find_user_by_name(target_name)
                    if target_id:
                        profile = self.get_or_create_profile(int(target_id))
                        clean_skill = self.clean_skill_name(skill_name)
                        if clean_skill not in profile['skills']['active']:
                            profile['skills']['active'].append(clean_skill)
                            self.save_profiles()
                            self.send_profile_to_admin(int(target_id), profile, f"(активный навык: +{clean_skill})")
                            self.send_message(peer_id, f"✅ {profile['name']}: добавлен активный навык '{clean_skill}'", self.get_keyboard())
                            return True
                        else:
                            self.send_message(peer_id, f"❌ Навык '{clean_skill}' уже есть у {profile['name']}", self.get_keyboard())
                            return True
                else:
                    profile = self.get_or_create_profile(user_id)
                    clean_skill = self.clean_skill_name(skill_name)
                    if clean_skill not in profile['skills']['active']:
                        profile['skills']['active'].append(clean_skill)
                        self.save_profiles()
                        self.send_profile_to_admin(user_id, profile, f"(активный навык: +{clean_skill})")
                        self.send_message(peer_id, f"✅ Добавлен активный навык '{clean_skill}'", self.get_keyboard())
                        return True
                    else:
                        self.send_message(peer_id, f"❌ Навык '{clean_skill}' уже есть", self.get_keyboard())
                        return True
            return False
        
        if command == 'пассивка':
            if len(parts) > 1:
                full_text = ' '.join(parts[1:])
                
                target_name = None
                skill_name = full_text
                
                words = full_text.split()
                if len(words) > 1:
                    potential_name = words[-1]
                    if self.find_user_by_name(potential_name):
                        target_name = potential_name
                        skill_name = ' '.join(words[:-1])
                
                if skill_name.endswith('+'):
                    skill_name = skill_name[:-1].strip()
                
                if target_name:
                    target_id = self.find_user_by_name(target_name)
                    if target_id:
                        profile = self.get_or_create_profile(int(target_id))
                        clean_skill = self.clean_skill_name(skill_name)
                        if clean_skill not in profile['skills']['passive']:
                            profile['skills']['passive'].append(clean_skill)
                            self.save_profiles()
                            self.send_profile_to_admin(int(target_id), profile, f"(пассивный навык: +{clean_skill})")
                            self.send_message(peer_id, f"✅ {profile['name']}: добавлен пассивный навык '{clean_skill}'", self.get_keyboard())
                            return True
                        else:
                            self.send_message(peer_id, f"❌ Навык '{clean_skill}' уже есть у {profile['name']}", self.get_keyboard())
                            return True
                else:
                    profile = self.get_or_create_profile(user_id)
                    clean_skill = self.clean_skill_name(skill_name)
                    if clean_skill not in profile['skills']['passive']:
                        profile['skills']['passive'].append(clean_skill)
                        self.save_profiles()
                        self.send_profile_to_admin(user_id, profile, f"(пассивный навык: +{clean_skill})")
                        self.send_message(peer_id, f"✅ Добавлен пассивный навык '{clean_skill}'", self.get_keyboard())
                        return True
                    else:
                        self.send_message(peer_id, f"❌ Навык '{clean_skill}' уже есть", self.get_keyboard())
                        return True
            return False
        
        if command == 'раса' and len(parts) > 1:
            race_name = ' '.join(parts[1:])
            target_name = None
            if len(parts) > 2:
                potential_name = parts[-1]
                if self.find_user_by_name(potential_name):
                    target_name = potential_name
                    race_name = ' '.join(parts[1:-1])
            
            if target_name:
                target_id = self.find_user_by_name(target_name)
                if target_id:
                    profile = self.get_or_create_profile(int(target_id))
                    old_race = profile['race']
                    profile['race'] = race_name
                    self.save_profiles()
                    self.send_profile_to_admin(int(target_id), profile, f"(раса: {old_race} → {race_name})")
                    self.send_message(peer_id, f"✅ {profile['name']}: раса изменена с '{old_race}' на '{race_name}'", self.get_keyboard())
                    return True
            else:
                profile = self.get_or_create_profile(user_id)
                old_race = profile['race']
                profile['race'] = race_name
                self.save_profiles()
                self.send_profile_to_admin(user_id, profile, f"(раса: {old_race} → {race_name})")
                self.send_message(peer_id, f"✅ Раса изменена с '{old_race}' на '{race_name}'", self.get_keyboard())
                return True
            return False
        
        if command == 'класс' and len(parts) > 1:
            class_name = ' '.join(parts[1:])
            target_name = None
            if len(parts) > 2:
                potential_name = parts[-1]
                if self.find_user_by_name(potential_name):
                    target_name = potential_name
                    class_name = ' '.join(parts[1:-1])
            
            if target_name:
                target_id = self.find_user_by_name(target_name)
                if target_id:
                    profile = self.get_or_create_profile(int(target_id))
                    old_class = profile['class']
                    profile['class'] = class_name
                    self.save_profiles()
                    self.send_profile_to_admin(int(target_id), profile, f"(класс: {old_class} → {class_name})")
                    self.send_message(peer_id, f"✅ {profile['name']}: класс изменен с '{old_class}' на '{class_name}'", self.get_keyboard())
                    return True
            else:
                profile = self.get_or_create_profile(user_id)
                old_class = profile['class']
                profile['class'] = class_name
                self.save_profiles()
                self.send_profile_to_admin(user_id, profile, f"(класс: {old_class} → {class_name})")
                self.send_message(peer_id, f"✅ Класс изменен с '{old_class}' на '{class_name}'", self.get_keyboard())
                return True
            return False
        
        return False

    def handle_message(self, event):
        message_data = event.obj['message']
        peer_id = message_data['peer_id']
        user_id = message_data['from_id']
        text = message_data['text'] if message_data['text'] else ""

        print(f"📩 {text}")

        if user_id < 0:
            return

        is_chat = peer_id > 2000000000
        clean_text = self.clean_text(text)
        is_admin = user_id in ADMIN_IDS

        is_forward = False
        forwarded_text = ""
        forwarded_user_id = None
        
        if 'fwd' in message_data and message_data['fwd']:
            is_forward = True
            for fwd in message_data['fwd']:
                if 'text' in fwd and fwd['text']:
                    forwarded_text = fwd['text']
                if 'from_id' in fwd:
                    forwarded_user_id = fwd['from_id']
                break
            
            if is_admin and forwarded_text and forwarded_user_id:
                self.last_forwarded[user_id] = {
                    'text': forwarded_text,
                    'user_id': forwarded_user_id,
                    'peer_id': peer_id
                }
                print(f"📎 Сохранено пересланное сообщение от {user_id} для игрока {forwarded_user_id}")

        # ===== ПОКАЗАТЬ ПРОФИЛЬ ИГРОКА =====
        if text.startswith('покажи профиль'):
            if not is_admin:
                self.send_message(peer_id, "❌ Эта команда доступна только администраторам.", self.get_keyboard())
                return
            
            parts = text.split()
            if len(parts) < 3:
                self.send_message(peer_id, "❌ Укажите имя игрока. Формат: покажи профиль Имя", self.get_keyboard())
                return
            
            player_name = ' '.join(parts[2:])
            target_id = self.find_user_by_name(player_name)
            
            if not target_id:
                self.send_message(peer_id, f"❌ Игрок с именем '{player_name}' не найден.", self.get_keyboard())
                return
            
            profile = self.get_profile(int(target_id))
            if profile:
                profile_text = self.format_profile(int(target_id))
                self.send_message(peer_id, f"📋 Профиль игрока '{player_name}':\n\n{profile_text}", self.get_keyboard())
            else:
                self.send_message(peer_id, f"❌ У игрока '{player_name}' нет профиля.", self.get_keyboard())
            return

        # ===== /игроки =====
        if clean_text == '/игроки':
            if not is_admin:
                self.send_message(peer_id, "❌ Эта команда доступна только администраторам.", self.get_keyboard())
                return
            
            players = self.get_all_players()
            if players:
                msg = "📋 **Список игроков:**\n\n"
                for i, name in enumerate(players, 1):
                    msg += f"{i}. {name}\n"
                self.send_message(peer_id, msg, self.get_keyboard())
            else:
                self.send_message(peer_id, "❌ Нет сохранённых профилей игроков.", self.get_keyboard())
            return

        # ===== КОМАНДА =====
        if clean_text == 'команда':
            if not is_admin:
                print(f"⛔ {user_id} пытался вызвать команду, но только админы могут это делать!")
                return
            help_msg = (
                "🎲 **Список команд для админов:**\n\n"
                "**Просмотр профилей:**\n"
                "• покажи профиль Имя - показать профиль игрока\n"
                "• /игроки - список всех игроков\n"
                "• /проф (с пересылкой) - показать профиль игрока по пересылке\n\n"
                "**Управление профилями:**\n"
                "• +проф (с пересылкой) - обновить свой профиль\n"
                "• игрок+ (с пересылкой) - создать/обновить профиль игрока\n"
                "• игрок- Имя - удалить профиль игрока\n\n"
                "**Изменение характеристик (+ и -):**\n"
                "• ст+5 Имя / ст-5 Имя - Стойкость\n"
                "• си+3 Имя / си-3 Имя - Сила\n"
                "• л+2 Имя / л-2 Имя - Ловкость\n"
                "• х+4 Имя / х-4 Имя - Харизма\n"
                "• и+1 Имя / и-1 Имя - Интеллект\n"
                "• хп+50 Имя / хп-50 Имя - ХП\n"
                "• броня+5 Имя / броня-5 Имя - Броня\n"
                "• атака+5 Имя / атака-5 Имя - Атака\n\n"
                "**Навыки:**\n"
                "• активка Навык+ - добавить активный навык\n"
                "• пассивка Навык+ - добавить пассивный навык\n\n"
                "**Прочее:**\n"
                "• раса Эльф Имя - изменить расу\n"
                "• класс Хилер Имя - изменить класс\n"
                "• кости+ / кости- - активировать/деактивировать бота"
            )
            self.send_message(peer_id, help_msg, self.get_keyboard())
            return

        # Активация/деактивация
        if clean_text in ['кости+', 'кости +']:
            if not is_admin:
                return
            if is_chat:
                self.active_chats.add(peer_id)
                self.send_message(peer_id, "🎲 Бот активирован!", self.get_keyboard())
            return

        if clean_text in ['кости-', 'кости -']:
            if not is_admin:
                return
            if is_chat and peer_id in self.active_chats:
                self.active_chats.discard(peer_id)
                self.send_message(peer_id, "🎲 Бот деактивирован!", self.get_clear_keyboard())
            return

        # /проф
        if text.startswith('/проф'):
            if not is_admin:
                self.send_message(peer_id, "❌ Эта команда доступна только администраторам.", self.get_keyboard())
                return
            
            if is_forward and forwarded_user_id:
                profile = self.get_profile(forwarded_user_id)
                if profile:
                    profile_text = self.format_profile(forwarded_user_id)
                    self.send_message(peer_id, f"📋 Профиль игрока:\n\n{profile_text}", self.get_keyboard())
                else:
                    self.send_message(peer_id, "❌ У этого игрока нет профиля.", self.get_keyboard())
            else:
                self.send_message(peer_id, "❌ Перешлите сообщение игрока, чей профиль хотите посмотреть.", self.get_keyboard())
            return

        # игрок+
        if text.lower().startswith('игрок+') and is_admin:
            if is_forward and forwarded_text and forwarded_user_id:
                print(f"📎 Создание профиля игрока из пересланного сообщения")
                parsed_data = self.parse_profile_from_text(forwarded_text)
                
                has_data = False
                for key, value in parsed_data.items():
                    if key == 'stats':
                        for stat, val in value.items():
                            if val is not None:
                                has_data = True
                                break
                    elif key == 'skills':
                        if value['active'] or value['passive']:
                            has_data = True
                    elif value is not None:
                        has_data = True
                    if has_data:
                        break
                
                if has_data:
                    profile = self.update_profile_from_data(forwarded_user_id, parsed_data)
                    profile_text = self.format_profile(forwarded_user_id)
                    self.send_message(peer_id, f"✅ Профиль игрока создан/обновлен!\n\n{profile_text}", self.get_keyboard())
                else:
                    self.send_message(peer_id, "❌ Не удалось распознать данные профиля из пересланного сообщения.", self.get_keyboard())
                return
            else:
                self.send_message(peer_id, "❌ Перешлите сообщение игрока с профилем вместе с командой 'игрок+'.", self.get_keyboard())
                return

        # игрок-
        if text.lower().startswith('игрок-') and is_admin:
            parts = text.split()
            if len(parts) < 2:
                self.send_message(peer_id, "❌ Укажите имя игрока. Формат: игрок- Имя", self.get_keyboard())
                return
            
            player_name = ' '.join(parts[1:])
            target_id = self.find_user_by_name(player_name)
            
            if not target_id:
                self.send_message(peer_id, f"❌ Игрок с именем '{player_name}' не найден.", self.get_keyboard())
                return
            
            if self.delete_profile(int(target_id)):
                self.send_message(peer_id, f"✅ Профиль игрока '{player_name}' удален.", self.get_keyboard())
            else:
                self.send_message(peer_id, f"❌ Профиль игрока '{player_name}' не найден.", self.get_keyboard())
            return

        # +проф / +профиль
        if text.startswith('+проф') or text.startswith('+профиль'):
            print(f"🔍 Обработка команды: {text[:50]}...")
            
            if is_forward and forwarded_text:
                print(f"📎 Обновление профиля из пересланного сообщения")
                parsed_data = self.parse_profile_from_text(forwarded_text)
                
                has_data = False
                for key, value in parsed_data.items():
                    if key == 'stats':
                        for stat, val in value.items():
                            if val is not None:
                                has_data = True
                                break
                    elif key == 'skills':
                        if value['active'] or value['passive']:
                            has_data = True
                    elif value is not None:
                        has_data = True
                    if has_data:
                        break
                
                if has_data:
                    profile = self.update_profile_from_data(user_id, parsed_data)
                    profile_text = self.format_profile(user_id)
                    self.send_message(peer_id, f"✅ Профиль обновлен из пересланного сообщения!\n\n{profile_text}", self.get_keyboard())
                else:
                    self.send_message(peer_id, "❌ Не удалось распознать данные профиля из пересланного сообщения.", self.get_keyboard())
                return
            
            if user_id in self.last_forwarded:
                forwarded_data = self.last_forwarded[user_id]
                forwarded_text = forwarded_data['text']
                print(f"📎 Используем сохранённое пересланное сообщение")
                
                parsed_data = self.parse_profile_from_text(forwarded_text)
                
                has_data = False
                for key, value in parsed_data.items():
                    if key == 'stats':
                        for stat, val in value.items():
                            if val is not None:
                                has_data = True
                                break
                    elif key == 'skills':
                        if value['active'] or value['passive']:
                            has_data = True
                    elif value is not None:
                        has_data = True
                    if has_data:
                        break
                
                if has_data:
                    profile = self.update_profile_from_data(user_id, parsed_data)
                    profile_text = self.format_profile(user_id)
                    self.send_message(peer_id, f"✅ Профиль обновлен из сохранённого пересланного сообщения!\n\n{profile_text}", self.get_keyboard())
                else:
                    self.send_message(peer_id, "❌ Не удалось распознать данные профиля из сохранённого сообщения.", self.get_keyboard())
                return
            
            self.send_message(peer_id, "❌ Перешлите сообщение с профилем вместе с командой +проф (одним сообщением).", self.get_keyboard())
            return

        # Мой профиль
        if clean_text in ['мой профиль', 'профиль']:
            profile = self.get_profile(user_id)
            if profile:
                profile_text = self.format_profile(user_id)
                self.send_message(peer_id, profile_text, self.get_keyboard())
            else:
                user_name = self.get_user_name(user_id)
                self.create_profile(user_id, user_name)
                profile_text = self.format_profile(user_id)
                self.send_message(peer_id, f"✅ Профиль создан!\n\n{profile_text}", self.get_keyboard())
            return

        # Проверка активности чата
        if is_chat and peer_id not in self.active_chats:
            print(f"⏸️ Чат {peer_id} не активен, игнорируем")
            return

        # Админские команды
        if is_admin and self.handle_admin_command(text, peer_id, user_id):
            return

        # Кости
        if clean_text in ['d6', 'д6']:
            result = self.roll_dice(6, user_id)
            name = self.get_user_name(user_id)
            self.send_message(peer_id, f"{name} бросил d6: {result}", self.get_keyboard())
        elif clean_text in ['d8', 'д8']:
            result = self.roll_dice(8, user_id)
            name = self.get_user_name(user_id)
            self.send_message(peer_id, f"{name} бросил d8: {result}", self.get_keyboard())
        elif clean_text in ['d10', 'д10']:
            result = self.roll_dice(10, user_id)
            name = self.get_user_name(user_id)
            self.send_message(peer_id, f"{name} бросил d10: {result}", self.get_keyboard())
        elif clean_text in ['d12', 'д12']:
            result = self.roll_dice(12, user_id)
            name = self.get_user_name(user_id)
            self.send_message(peer_id, f"{name} бросил d12: {result}", self.get_keyboard())
        elif clean_text in ['d20', 'д20']:
            result = self.roll_dice(20, user_id)
            name = self.get_user_name(user_id)
            msg = f"{name} бросил d20: {result}"
            if result == 20:
                msg += "\n🔥 КРИТИЧЕСКИЙ УСПЕХ! 🔥"
            elif result == 1:
                msg += "\n☠ ГОТОВЬ ЕБАЛЬНИК! ☠"
            self.send_message(peer_id, msg, self.get_keyboard())
        elif not is_chat:
            self.send_message(peer_id, "Нажимайте на кнопки:", self.get_keyboard())

    def run(self):
        print("=" * 50)
        print("🎲 Бот запущен!")
        print("👑 Админы: Екатерина, Велес")
        print("⚖️ Все игроки бросают кости с одинаковыми шансами!")
        print("💚 1 Стойкость = 10 HP")
        print("📊 Модификаторы округляются в большую сторону (потолок)")
        print("👤 Для всех: кнопка 'Мой профиль'")
        print("🔧 Команды админов в списке 'Команда'")
        print("🔄 + и - для изменения характеристик")
        print("📋 покажи профиль Имя - посмотреть профиль игрока")
        print("📩 Все изменения профилей дублируются в ЛС Екатерине")
        print("💾 Профили сохраняются в profiles.json")
        print("=" * 50)

        for event in self.longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_NEW:
                if event.obj['message']['text'] is not None:
                    try:
                        self.handle_message(event)
                    except Exception as e:
                        print(f"❌ {e}")


if __name__ == "__main__":
    bot = VKBot(VK_TOKEN, GROUP_ID)
    bot.run()
