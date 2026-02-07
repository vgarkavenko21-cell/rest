# admin.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import os

class Admin:
    def __init__(self, database, password):
        self.db = database
        self.admin_password = password
        self.admin_sessions = set()
        self.temp_items = {}
    
    def verify_password(self, password):
        return password == self.admin_password
    
    def add_admin_session(self, user_id):
        self.admin_sessions.add(user_id)
    
    def is_admin(self, user_id):
        return user_id in self.admin_sessions
    
    async def show_admin_panel(self, message):
        keyboard = [
            [InlineKeyboardButton("🍽 Додати страву", callback_data="admin_add_item")],
            [InlineKeyboardButton("📦 Всі замовлення", callback_data="admin_all_orders")],
            [InlineKeyboardButton("🔙 Головне меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "👨‍💼 Панель адміністратора\n"
            "Оберіть дію:",
            reply_markup=reply_markup
        )
    
    async def handle_callback(self, query, data, user_id, user_states):
        if data == "admin_add_item":
            await self.start_add_item(query)
        elif data.startswith("admin_category_"):
            category = data.split("_")[2]
            user_states[user_id] = f"admin_add_item_{category}_name"
            await query.edit_message_text(f"Введіть назву страви для категорії {category}:")
        elif data == "admin_all_orders":
            await self.show_all_orders(query)
        elif data.startswith("admin_order_"):
            order_id = data.split("_")[2]
            await self.show_order_details(query, order_id)
        elif data.startswith("admin_change_status_"):
            parts = data.split("_")
            order_id = parts[3]
            new_status = parts[4]
            await self.change_order_status(query, order_id, new_status)
        elif data == "admin_back":
            await self.show_admin_panel(query.message)
    
    async def start_add_item(self, query):
        categories = self.db.get_categories()
        keyboard = []
        
        for category_id, category_data in categories.items():
            keyboard.append([InlineKeyboardButton(
                category_data["name"], 
                callback_data=f"admin_category_{category_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🍽 Оберіть категорію для нової страви:",
            reply_markup=reply_markup
        )
    
    async def show_all_orders(self, query):
        orders = self.db.get_all_orders()
        
        if not orders:
            await query.edit_message_text("📦 Немає замовлень")
            return
        
        keyboard = []
        
        for order_id, order in list(orders.items())[-10:]:  # Останні 10 замовлень
            status_icons = {
                "new": "🆕",
                "confirmed": "✅",
                "cooking": "👨‍🍳", 
                "delivery": "🚗",
                "delivered": "📦",
                "cancelled": "❌"
            }
            status_icon = status_icons.get(order.get("status", "new"), "📝")
            
            # БЕЗПЕЧНИЙ спосіб отримати delivery_time
            delivery_time = order.get('delivery_time', '?')
            
            # Якщо delivery_time є числом або None, перетворюємо на рядок
            if delivery_time is None:
                delivery_time_display = "?"
            elif isinstance(delivery_time, (int, float)):
                # Якщо це час у хвилинах або годинах
                if delivery_time > 60:
                    hours = int(delivery_time / 60)
                    minutes = int(delivery_time % 60)
                    delivery_time_display = f"{hours}:{minutes:02d}"
                else:
                    delivery_time_display = f"{int(delivery_time)}хв"
            elif isinstance(delivery_time, str):
                if delivery_time == "Якомога швидше":
                    delivery_time_display = "🚀"
                elif len(delivery_time) > 5:
                    delivery_time_display = delivery_time[:5]
                else:
                    delivery_time_display = delivery_time
            else:
                # Якщо якийсь інший тип
                delivery_time_display = str(delivery_time)[:5]
            
            # Текст кнопки
            order_status = order.get('status', 'new')
            button_text = f"{status_icon} #{order_id[:6]} | {delivery_time_display} | {order_status}"
            
            # Скорочуємо якщо занадто довго
            if len(button_text) > 35:
                button_text = f"{status_icon} #{order_id[:6]} | {order_status}"
            
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"admin_order_{order_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔄 Оновити", callback_data="admin_all_orders")])
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_back")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📦 Оберіть замовлення (останні 10):",
            reply_markup=reply_markup
        )
        
        await query.edit_message_text(
            "📦 Оберіть замовлення:",
            reply_markup=reply_markup
        )
    
    async def show_order_details(self, query, order_id):
        orders = self.db.get_all_orders()
        order = orders.get(order_id)
        
        if not order:
            await query.answer("Замовлення не знайдено!")
            return
        
        order_text = f"📦 *Замовлення #{order_id}*\n\n"
        
        order_text += f"💰 *Сума:* {order['total']}₴\n"
        order_text += f"🏠 *Адреса:* {order['delivery_address']}\n"
        order_text += f"⏰ *Час доставки:* {order.get('delivery_time', 'Не вказано')}\n"
        order_text += f"📊 *Статус:* {order['status']}\n"
        order_text += f"📅 *Створено:* {order['created_at'][:16]}\n\n"
        
        order_text += "*Страви:*\n"
        for item_key, item_data in order['items'].items():
            item_total = item_data["price"] * item_data["quantity"]
            order_text += f"• {item_data['name']} x{item_data['quantity']} - {item_total}₴\n"
        
        keyboard = []
        statuses = [
            ("🆕 Змінити на Новий", "new"),
            ("✅ Змінити на Підтверджено", "confirmed"),
            ("👨‍🍳 Змінити на Готується", "cooking"),
            ("🚗 Змінити на В дорозі", "delivery"),
            ("📦 Змінити на Доставлено", "delivered"),
            ("❌ Змінити на Скасовано", "cancelled")
        ]
        
        for status_text, status_value in statuses:
            if order['status'] != status_value:
                keyboard.append([InlineKeyboardButton(
                    status_text, 
                    callback_data=f"admin_change_status_{order_id}_{status_value}"
                )])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад до списку", callback_data="admin_all_orders")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(order_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def change_order_status(self, query, order_id, new_status):
        if self.db.update_order_status(order_id, new_status):
            await query.answer(f"✅ Статус змінено на: {new_status}")
            
            # Якщо статус змінений на delivered або cancelled, замовлення повинно зникнути з "Чеку"
            # і з'явитися тільки в "Історії"
            if new_status in ['delivered', 'cancelled']:
                await query.edit_message_text(
                    f"✅ Статус замовлення #{order_id} змінено на: {new_status}\n"
                    f"📝 Це замовлення тепер буде показуватися тільки в 'Історії' користувача."
                )
            else:
                await self.show_order_details(query, order_id)
        else:
            await query.answer("❌ Помилка зміни статусу")