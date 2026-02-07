import json
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.data_file = "data1.json"
        self.init_database()
    
    def init_database(self):
        if not os.path.exists(self.data_file):
            default_data = {
                "categories": {
                    "breakfast": {
                        "name": "🍳 Сніданки",
                        "items": {}
                    },
                    "hot": {
                        "name": "🍲 Гарячі страви", 
                        "items": {}
                    },
                    "salads": {
                        "name": "🥗 Салати",
                        "items": {}
                    },
                    "meat": {
                        "name": "🍖 М'ясо",
                        "items": {}
                    },
                    "cold": {
                        "name": "🥪 Холодні закуски",
                        "items": {}
                    }
                },
                "orders": {},
                "users": {},
                "favorites": {},
                "settings": {
                    "delivery_price": 50,
                    "min_order": 100
                }
            }
            self.save_data(default_data)
    
    def load_data(self):
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_data(self, data):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_categories(self):
        data = self.load_data()
        return data["categories"]
    
    def get_category(self, category_id):
        data = self.load_data()
        return data["categories"].get(category_id)
    
    def get_category_items(self, category):
        data = self.load_data()
        return data["categories"][category]["items"]
    
    def get_item(self, category, item_id):
        data = self.load_data()
        return data["categories"][category]["items"].get(item_id)
    
    def add_category_item(self, category, item_data):
        data = self.load_data()
        item_id = str(int(datetime.now().timestamp()))
        data["categories"][category]["items"][item_id] = item_data
        self.save_data(data)
        return item_id
    
    def delete_category_item(self, category, item_id):
        data = self.load_data()
        if category in data["categories"] and item_id in data["categories"][category]["items"]:
            del data["categories"][category]["items"][item_id]
            self.save_data(data)
            return True
        return False
    
    def create_order(self, user_id, cart_items, contact_info, total, order_type="🚗 Доставка"):
        data = self.load_data()
        order_id = str(int(datetime.now().timestamp()))
        
        order = {
            "user_id": user_id,
            "items": cart_items,
            "total": total,
            "contact_info": contact_info,
            "order_type": order_type,
            "status": "new",
            "is_paid": False,
            "payment_method": "cash",
            "created_at": datetime.now().isoformat()
        }
        
        data["orders"][order_id] = order
        self.save_data(data)
        return order_id
    
    def update_order_status(self, order_id, new_status):
        data = self.load_data()
        if order_id in data["orders"]:
            data["orders"][order_id]["status"] = new_status
            self.save_data(data)
            return True
        return False
    
    def get_all_orders(self):
        data = self.load_data()
        return data["orders"]
    
    def get_user_orders(self, user_id):
        data = self.load_data()
        user_orders = {}
        for order_id, order in data["orders"].items():
            if order["user_id"] == user_id:
                user_orders[order_id] = order
        return user_orders
    
    def get_user_favorites(self, user_id):
        """Отримуємо улюблені страви користувача"""
        data = self.load_data()
        user_id_str = str(user_id)
        
        # Перевіряємо, чи існує розділ favorites
        if "favorites" not in data:
            data["favorites"] = {}
            self.save_data(data)
            return []  # Повертаємо порожній список
        
        # Повертаємо список улюблених для користувача
        favorites = data.get("favorites", {}).get(user_id_str, [])
        # Перевірка на None або порожній список
        return favorites if favorites else []
    
    def add_user_favorite(self, user_id, item_data):
        """Додаємо страву до улюблених"""
        data = self.load_data()
        user_id_str = str(user_id)
    
        # Ініціалізуємо структури, якщо їх немає
        if "favorites" not in data:
           data["favorites"] = {}
    
        if user_id_str not in data["favorites"]:
            data["favorites"][user_id_str] = []
    
        # Перевіряємо, чи вже є така страва (за назвою)
        existing_favorites = data["favorites"][user_id_str]
        item_name = item_data.get('name', '')
    
        # ВИПРАВЛЕННЯ: Перевіряємо за ID, а не за назвою
        item_id = item_data.get('id', '')
        for fav in existing_favorites:
           if fav.get('id') == item_id:  # Змінити тут
               # Страва вже в улюблених
              return False
    
     # Додаємо нову страву
        data["favorites"][user_id_str].append(item_data)
        self.save_data(data)
        return True
    
    def clear_user_favorites(self, user_id):
        """Очистити всі улюблені страви користувача"""
        data = self.load_data()
        user_id_str = str(user_id)
        
        if "favorites" in data and user_id_str in data["favorites"]:
            data["favorites"][user_id_str] = []
            self.save_data(data)
            return True
        
        return False
    
    def remove_user_favorite(self, user_id, item_id):
        """Видаляємо страву з улюблених"""
        data = self.load_data()
        user_id_str = str(user_id)
        
        if "favorites" in data and user_id_str in data["favorites"]:
            # Фільтруємо список, залишаючи всі страви крім тієї, що треба видалити
            original_count = len(data["favorites"][user_id_str])
            data["favorites"][user_id_str] = [
                fav for fav in data["favorites"][user_id_str]
                if fav.get('id') != item_id
            ]
            
            # Якщо список змінився, зберігаємо
            if len(data["favorites"][user_id_str]) != original_count:
                self.save_data(data)
                return True
        
        return False