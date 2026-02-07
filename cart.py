from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime

class Cart:
    def __init__(self, database):
        self.db = database
        self.user_carts = {}
        self.user_temp_data = {}  # Для збереження даних перед підтвердженням
        self.user_table_info = {}  # Зберігаємо інформацію про столик для кожного користувача
    
    def get_user_cart(self, user_id):
        if user_id not in self.user_carts:
            self.user_carts[user_id] = {}
        return self.user_carts[user_id]
    
    def get_user_table_info(self, user_id):
        """Отримуємо інформацію про столик користувача"""
        return self.user_table_info.get(user_id)
    
    def set_user_table_info(self, user_id, table_info):
        """Зберігаємо інформацію про столик користувача"""
        self.user_table_info[user_id] = table_info
    
    async def add_to_cart(self, query, category, item_id):
        user_id = query.from_user.id
        cart = self.get_user_cart(user_id)
        item = self.db.get_item(category, item_id)
        
        if not item:
            await query.answer("❌ Страва не знайдена!")
            return
        
        cart_key = f"{category}_{item_id}"
        if cart_key in cart:
            cart[cart_key]["quantity"] += 1
        else:
            cart[cart_key] = {
                "name": item["name"],
                "price": item["price"],
                "quantity": 1
            }
        await query.answer(f"✅ {item['name']} додано до кошика!")

    # 1. КОШИК (ЧЕРНЕТКА)
    async def show_cart(self, message, order_type):
        user_id = message.from_user.id
        cart = self.get_user_cart(user_id)
        
        if not cart:
            keyboard = [[KeyboardButton("🍽 Меню")], [KeyboardButton("🧾 Чек"), KeyboardButton("❤️ Улюблене")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await message.reply_text("🛒 Ваш кошик порожній. Додайте страви з меню.", reply_markup=reply_markup)
            return
        
        total = 0
        text = "🛒 <b>ВАШ КОШИК</b>\n\n"
        for item in cart.values():
            subtotal = item["price"] * item["quantity"]
            total += subtotal
            text += f"▫️ {item['name']} x{item['quantity']} = {subtotal}₴\n"
        
        text += f"\n<b>Разом: {total}₴</b>"
        
        # Перевіряємо, чи є вже активне замовлення в закладі
        table_info = self.get_user_table_info(user_id)
        if table_info:
            text += f"\n\n📌 <b>Це замовлення буде додано до вашого активного чеку</b>"
            text += f"\n📍 Столик: {table_info}"
        
        keyboard = [
            [KeyboardButton("✅ Підтвердити замовлення")],
            [KeyboardButton("🗑 Очистити кошик"), KeyboardButton("🍽 Меню")],
            [KeyboardButton("🔙 Головне меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    # 2. ЗАПИТ ДАНИХ (СТОЛИК АБО АДРЕСА) - тільки якщо треба
    async def request_info(self, message, order_type):
        user_id = message.from_user.id
        
        # Перевіряємо, чи є вже інформація про столик для замовлень в закладі
        if order_type == "🏠 В закладі":
            table_info = self.get_user_table_info(user_id)
            if table_info:
                # Якщо вже є активне замовлення в закладі, використовуємо той самий столик
                await self.confirm_order(message, table_info, order_type)
                return
        
        keyboard = [[KeyboardButton("🔙 Кошик")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if order_type == "🏠 В закладі":
            text = "🍽 <b>Введіть номер вашого столика:</b>\n(Просто цифру, наприклад: 5)"
        else:
            text = "🚚 <b>Введіть адресу доставки:</b>\n(Вулиця, будинок, під'їзд, квартира)"
            
        await message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    # 3. ПІДТВЕРДЖЕННЯ ТА ЗБЕРЕЖЕННЯ В БАЗУ
    async def confirm_order(self, message, info_text, order_type):
        user_id = message.from_user.id
        cart = self.get_user_cart(user_id)
        
        if not cart:
            await message.reply_text("❌ Помилка: кошик порожній.")
            return

        total = sum(item["price"] * item["quantity"] for item in cart.values())
        
        # Для замовлень в закладі зберігаємо інформацію про столик
        if order_type == "🏠 В закладі":
            self.set_user_table_info(user_id, info_text)
        
        # Для доставки додаємо вартість доставки
        if order_type == "🚗 Доставка":
            delivery_price = self.db.load_data()["settings"]["delivery_price"]
            total += delivery_price
        
        # Створюємо замовлення
        order_id = self.db.create_order(user_id, cart, info_text, total, order_type)
        
        # Очищуємо кошик
        self.user_carts[user_id] = {}
        
        # Формуємо клавіатуру для переходу до чеку
        keyboard = [
            [KeyboardButton("🍽 Меню"), KeyboardButton("🧾 Чек")],
            [KeyboardButton("🔙 Головне меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await message.reply_text(
            f"✅ <b>Замовлення #{order_id} створено!</b>\n"
            f"Тепер воно доступне в меню '🧾 Чек' де ви можете його оплатити.",
            reply_markup=reply_markup, parse_mode="HTML"
        )

    # 3. ПІДТВЕРДЖЕННЯ ТА ЗБЕРЕЖЕННЯ В БАЗУ
    async def confirm_order(self, message, info_text, order_type):
        user_id = message.from_user.id
        cart = self.get_user_cart(user_id)
        
        if not cart:
            await message.reply_text("❌ Помилка: кошик порожній.")
            return

        total = sum(item["price"] * item["quantity"] for item in cart.values())
        
        # Для замовлень в закладі зберігаємо інформацію про столик
        if order_type == "🏠 В закладі":
            self.set_user_table_info(user_id, info_text)
        
        # Для доставки додаємо вартість доставки
        if order_type == "🚗 Доставка":
            delivery_price = self.db.load_data()["settings"]["delivery_price"]
            total += delivery_price
        
        # Створюємо замовлення
        order_id = self.db.create_order(user_id, cart, info_text, total, order_type)
        
        # Очищуємо кошик
        self.user_carts[user_id] = {}
        
        # Формуємо клавіатуру для переходу до чеку
        keyboard = [
            [KeyboardButton("🍽 Меню"), KeyboardButton("🧾 Чек")],
            [KeyboardButton("🔙 Головне меню")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Визначаємо info_label в залежності від типу замовлення
        if order_type == "🏠 В закладі":
            info_label = "Стіл"
        else:
            info_label = "Адреса"
        
        # Показуємо, що замовлення додано до активного чеку
        existing_orders = self.db.get_user_orders(user_id)
        active_count = 0
        for oid, order in existing_orders.items():
            if (order.get('order_type') == order_type and 
                order.get('status') == 'new' and 
                order.get('contact_info') == info_text):
                active_count += 1
        
        if active_count > 1:
            message_text = f"✅ <b>Замовлення #{order_id} додано до активного чеку!</b>\n"
            message_text += f"📋 У чеку вже {active_count} замовлень\n"
            message_text += f"📍 {info_label}: {info_text}\n"
            message_text += f"💰 Загальна сума в чеку: буде показана при перегляді"
        else:
            message_text = f"✅ <b>Замовлення створено!</b>\n"
            message_text += f"Тепер воно доступне в меню '🧾 Чек' де ви можете його оплатити."
        
        await message.reply_text(message_text, reply_markup=reply_markup, parse_mode="HTML")


    # 4. ЧЕК / АКТИВНІ ЗАМОВЛЕННЯ (З кнопкою оплати)
    async def show_active_check(self, message, current_order_type):
        user_id = message.from_user.id
        orders = self.db.get_user_orders(user_id)
        
        # Фільтруємо: показуємо тільки замовлення поточного типу зі статусом "new"
        active_orders = {}
        active_order_ids = []
        
        for order_id, order in orders.items():
            status = order.get('status', 'new')
            order_type = order.get('order_type', '🚗 Доставка')
            
            if order_type == current_order_type and status == 'new':
                active_orders[order_id] = order
                active_order_ids.append(order_id)
        
        if not active_orders:
            type_text = "доставки" if current_order_type == "🚗 Доставка" else "в закладі"
            await message.reply_text(f"📭 У вас немає активних замовлень {type_text}.")
            return active_order_ids
        
        # Групуємо замовлення за столиком/адресою
        grouped_orders = {}
        for order_id, order in active_orders.items():
            contact_info = order.get('contact_info', '')
            if contact_info not in grouped_orders:
                grouped_orders[contact_info] = []
            grouped_orders[contact_info].append((order_id, order))
        
        # Виводимо кожну групу як ОДИН чек
        for contact_info, orders_list in grouped_orders.items():
            # Тип замовлення вже відомий (current_order_type)
            if current_order_type == "🏠 В закладі":
                icon = "🏠"
                info_label = "Стіл"
            else:
                icon = "🚗"
                info_label = "Адреса"
            
            # Початок чеку
            text = f"{icon} <b>ЧЕК</b>\n"
            text += f"📍 {info_label}: {contact_info}\n\n"
            
            # ОБ'ЄДНУЄМО всі замовлення в одному списку страв
            text += "<b>Список страв:</b>\n"
            
            # Словник для об'єднання однакових страв
            all_items = {}
            total_all = 0
            order_ids = []
            
            for order_id, order in orders_list:
                order_ids.append(order_id)
                
                # Додаємо страви до загального списку
                for item in order['items'].values():  # Змінено - без item_key
                    item_name = item['name']
                    if item_name in all_items:
                        all_items[item_name]['quantity'] += item['quantity']
                        all_items[item_name]['subtotal'] += item['price'] * item['quantity']
                    else:
                        all_items[item_name] = {
                            'price': item['price'],
                            'quantity': item['quantity'],
                            'subtotal': item['price'] * item['quantity']
                        }
                    
                    total_all += item['price'] * item['quantity']
            
            # Виводимо об'єднаний список страв
            for item_name, item_data in all_items.items():
                text += f"▫️ {item_name} | {item_data['quantity']}шт. x {item_data['price']}₴ = {item_data['subtotal']}₴\n"
            
            if current_order_type == "🚗 Доставка":
                text += "\n🚚 Доставка: включено"
                
            text += f"\n💰 <b>ЗАГАЛЬНА СУМА ДО СПЛАТИ: {total_all}₴</b>"
            
            # Кнопки оплати
            keyboard = []
            orders_str = "_".join(order_ids)
            
            # Кнопка оплати всього чеку
            callback_data = f"pay_all_{orders_str}"
            if len(callback_data) < 64:
                keyboard.append([
                    InlineKeyboardButton(
                        f"💳 Оплатити({total_all}₴)", 
                        callback_data=callback_data
                    )
                ])
            
            # Інлайн-повідомлення з кнопками оплати
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
        
        # Повертаємо ID активних замовлень
        return active_order_ids

    # 5. ІСТОРІЯ (Всі замовлення) - без змін
    async def show_history(self, message):
        user_id = message.from_user.id
        orders = self.db.get_user_orders(user_id)
        
        # Фільтруємо: беремо всі, сортуємо від нових
        sorted_orders = sorted(orders.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)
        
        if not sorted_orders:
            await message.reply_text("📜 Історія замовлень порожня.")
            return
        
        text = "📜 <b>ІСТОРІЯ ВСІХ ЗАМОВЛЕНЬ</b>\n\n"
        count = 0
        for order_id, order in sorted_orders:
            if count >= 10:  # Показати останні 10
                break
            
            # Іконка типу замовлення
            order_type = order.get('order_type', '🚗 Доставка')
            if order_type == "🏠 В закладі":
                type_icon = "🏠"
            else:
                type_icon = "🚗"
            
            # Іконка статусу
            status_icons = {
                "new": "🆕",
                "confirmed": "✅",
                "cooking": "👨‍🍳", 
                "delivery": "🚗",
                "delivered": "📦",
                "cancelled": "❌"
            }
            status_icon = status_icons.get(order.get('status', 'new'), "📝")
            
            text += f"{type_icon}{status_icon} <b>#{order_id}</b> | {order.get('created_at', '')[:16]}\n"
            
            # Тип
            type_text = "В закладі" if order_type == "🏠 В закладі" else "Доставка"
            text += f"Тип: {type_text}\n"
            
            # Статус
            status_display = {
                "new": "НОВИЙ",
                "confirmed": "ПІДТВЕРДЖЕНО",
                "cooking": "ГОТУЄТЬСЯ", 
                "delivery": "В ДОРОЗІ",
                "delivered": "ДОСТАВЛЕНО",
                "cancelled": "СКАСОВАНО"
            }
            status_text = status_display.get(order.get('status', 'new'), order.get('status', 'new').upper())
            text += f"Статус: {status_text}\n"
            
            # Стислий список страв
            items_list = ", ".join([f"{i['name']} ({i['quantity']})" for i in order['items'].values()])
            if len(items_list) > 50:
                text += f"Страви: {items_list[:50]}...\n"
            else:
                text += f"Страви: {items_list}\n"
            
            text += f"Сума: <b>{order.get('total', 0)}₴</b>\n"
            text += "──────────────────\n"
            count += 1
            
        await message.reply_text(text, parse_mode="HTML")

    # 6. ОЧИСТКА кошика (без змін)
    async def clear_cart(self, message):
        user_id = message.from_user.id
        self.user_carts[user_id] = {}
        await message.reply_text("🗑 Кошик очищено!")

    # 7. ОБРОБКА ОПЛАТИ (одиничного замовлення)
    async def process_payment(self, query, order_id):
        """Оплата одного замовлення"""
        try:
            data = self.db.load_data()
            
            if order_id not in data["orders"]:
                await query.answer("❌ Замовлення не знайдено", show_alert=True)
                return
            
            # Оновлюємо замовлення
            data["orders"][order_id]["is_paid"] = True
            data["orders"][order_id]["status"] = "confirmed"
            data["orders"][order_id]["paid_at"] = datetime.now().isoformat()
            
            self.db.save_data(data)
            
            # Очищуємо інформацію про столик для замовлень в закладі
            order = data["orders"][order_id]
            if order.get('order_type') == "🏠 В закладі":
                user_id = order.get('user_id')
                if user_id in self.user_table_info:
                    del self.user_table_info[user_id]
            
            # Повідомлення про успішну оплату
            await query.answer("✅ Оплата успішна!", show_alert=True)
            
            order_total = order.get('total', 0)
            await query.edit_message_text(
                f"✅ <b>ЧЕК #{order_id} СПЛАЧЕНО!</b>\n\n"
                f"💰 Сума: {order_total}₴\n\n"
                f"Дякуємо за замовлення! Очікуйте обслуговування.",
                parse_mode="HTML"
            )
            
        except Exception as e:
            print(f"Помилка в process_payment: {e}")
            await query.answer("❌ Помилка при оплаті", show_alert=True)

    
     # 8. ОБРОБКА ОПЛАТИ ВСЬОГО ЧЕКУ
    async def process_payment_all(self, query, order_ids):
        """Оплата всіх замовлень в чеку"""
        try:
            # Якщо order_ids - це рядок, розділяємо його
            if isinstance(order_ids, str):
                if order_ids:
                    order_ids = order_ids.split('_')
                else:
                    order_ids = []
            
            if not order_ids:
                await query.answer("❌ Немає замовлень для оплати", show_alert=True)
                return
            
            # Отримуємо загальну суму
            data = self.db.load_data()
            total_amount = 0
            user_id = None
            order_type = None
            
            for order_id in order_ids:
                order = data["orders"].get(order_id)
                if order:
                    total_amount += order.get('total', 0)
                    if not user_id:
                        user_id = order.get('user_id')
                        order_type = order.get('order_type')
            
            # Просто позначаємо всі замовлення як оплачені
            for order_id in order_ids:
                # Оновлюємо в базі даних
                if order_id in data["orders"]:
                    data["orders"][order_id]["is_paid"] = True
                    data["orders"][order_id]["status"] = "confirmed"
                    data["orders"][order_id]["paid_at"] = datetime.now().isoformat()
            
            # Зберігаємо зміни
            self.db.save_data(data)
            
            # Очищуємо інформацію про столик для замовлень в закладі
            if order_type == "🏠 В закладі" and user_id:
                if user_id in self.user_table_info:
                    del self.user_table_info[user_id]
            
            # Повідомлення про успішну оплату
            await query.answer("✅ Весь чек сплачено успішно!", show_alert=True)
            
            # Оновлюємо повідомлення
            await query.edit_message_text(
                f"✅ <b>ЧЕК СПЛАЧЕНО!</b>\n\n"
                f"📊 Оплачено замовлень: {len(order_ids)}\n"
                f"💰 Загальна сума: {total_amount}₴\n\n"
                f"Дякуємо за замовлення! Очікуйте обслуговування.",
                parse_mode="HTML"
            )
            
        except Exception as e:
            print(f"Помилка в process_payment_all: {e}")
            await query.answer("❌ Помилка при оплаті", show_alert=True)
            await query.edit_message_text(
                f"❌ <b>Сталася помилка при оплаті</b>\n\n"
                f"Будь ласка, зверніться до адміністратора.",
                parse_mode="HTML"
            )