import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

class Favorites:
    def __init__(self, database, cart):
        self.db = database
        self.cart = cart
        self.user_selections = {}
    
    def _generate_short_id(self, item_name):
        """Генерує короткий стабільний ID для страви на основі назви"""
        return hashlib.md5(item_name.encode('utf-8')).hexdigest()[:10]

    async def show_favorites_menu(self, message, is_update=False):
        """Показуємо меню улюблених страв.
           is_update=True використовується, якщо ми редагуємо існуюче повідомлення.
        """
        user_id = message.from_user.id
        
        # Отримуємо улюблені страви
        favorites = self.db.get_user_favorites(user_id)
        
        # Навігаційна клавіатура (Тільки якщо це нове повідомлення)
        if not is_update:
            nav_keyboard = [
                [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
                [KeyboardButton("🧾 Чек"), KeyboardButton("🔙 Головне меню")]
            ]
            await message.reply_text(
                "Оберіть дію:",
                reply_markup=ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)
            )
        
        # Перевіряємо чи є улюблені
        if not favorites:
            text = (
                "❤️ <b>УЛЮБЛЕНІ СТРАВИ</b>\n\n"
                "✨ <b>СУПЕР!</b> Тут будуть ваші улюблені страви!\n\n"
                "📌 Щоб додати страви в улюблене:\n"
                "1. Зробіть замовлення\n"
                "2. Перейдіть в '🧾 Чек'\n"
                "3. Натисніть '❤️ Додати в улюблене'\n\n"
                "🔥 Це дозволить швидко повторювати улюблені замовлення!"
            )
            if is_update:
                try:
                    await message.edit_text(text, parse_mode="HTML")
                except:
                    pass 
            else:
                await message.reply_text(text, parse_mode="HTML")
            return
        
        # Генеруємо клавіатуру з актуальними даними кошика
        reply_markup = self._build_favorites_keyboard(user_id, favorites)
        
        text = (
            "❤️ <b>ВАШІ УЛЮБЛЕНІ СТРАВИ</b>\n"
            "👇 Оберіть страви для швидкого замовлення:"
        )

        if is_update:
            # Якщо текст не змінився, Telegram викине помилку, тому ігноруємо її
            try:
                await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
            except Exception:
                # Якщо текст той самий, просто оновлюємо кнопки
                try:
                    await message.edit_reply_markup(reply_markup=reply_markup)
                except:
                    pass
        else:
            await message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    def _build_favorites_keyboard(self, user_id, favorites):
        """Допоміжна функція для створення кнопок"""
        user_cart = self.cart.get_user_cart(user_id)
        keyboard = []
        
        for fav in favorites[:10]: # Ліміт 10 страв для краси
            item_id = fav.get('id', '')
            item_name = fav.get('name', 'Невідома страва')
            
            if not item_id:
                continue
            
            # Перевіряємо, чи ця страва вже в кошику
            quantity = 0
            cart_key = f"fav_{item_id}"
            
            if cart_key in user_cart:
                quantity = user_cart[cart_key]['quantity']
            
            # Формуємо вигляд кнопки
            if quantity > 0:
                emoji_numbers = {
                    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
                    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
                }
                counter = emoji_numbers.get(quantity, f"{quantity} шт.")
                # Кнопка для видалення (або зменшення)
                button_text = f"{counter} {item_name}"
                callback_data = f"fav_remove_{item_id}"
            else:
                # Кнопка додавання
                button_text = f"➕ {item_name}"
                callback_data = f"fav_add_{item_id}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Кнопки управління
        controls = []
        if len(favorites) > 1:
             keyboard.append([InlineKeyboardButton("🛒 Додати всі до кошика", callback_data="fav_add_all")])
        
        keyboard.append([InlineKeyboardButton("🗑 Очистити улюблені", callback_data="fav_clear")])
        
        return InlineKeyboardMarkup(keyboard)

    async def start_add_favorites(self, message, order_ids):
        """Початок додавання страв в улюблені з чеку"""
        user_id = message.from_user.id
        data = self.db.load_data()
        unique_items = []
        seen_names = set()
        
        # Збираємо страви з історії замовлень
        for order_id in order_ids:
            order = data.get("orders", {}).get(order_id)
            if order and str(order.get("user_id")) == str(user_id):
                for item in order.get("items", {}).values():
                    item_name = item.get("name", "")
                    if item_name and item_name not in seen_names:
                        seen_names.add(item_name)
                        
                        # ВАЖЛИВО: Генеруємо короткий ID, щоб кнопка працювала
                        short_id = self._generate_short_id(item_name)
                        
                        unique_items.append({
                            'id': short_id, 
                            'name': item_name,
                            'price': item.get("price", 0),
                            'quantity': 1 # Дефолтна кількість для збереження
                        })
        
        if not unique_items:
            await message.reply_text("❌ У цьому чеку немає страв для додавання.")
            return
        
        self.user_selections[user_id] = {
            'items': unique_items,
            'selected': set()
        }
        
        await self._update_selection_message(message, user_id, is_new=True)

    async def handle_favorites_callback(self, query, data, user_id):
        """Обробка всіх callback для улюблених"""
        # Не викликаємо query.answer() тут, робимо це в конкретних методах
        
        if data == "fav_select_all":
            await self._select_all(query, user_id)
        elif data == "fav_deselect_all":
            await self._deselect_all(query, user_id)
        elif data == "fav_save":
            await self._save_favorites(query, user_id)
        elif data == "fav_cancel":
            await self._cancel_selection(query, user_id)
        elif data == "fav_add_all":
            await self._add_all_to_cart(query, user_id)
        elif data == "fav_clear":
            await self._clear_favorites(query, user_id)
        elif data.startswith("fav_select_"):
            await self._handle_selection(query, data, user_id)
        elif data.startswith("fav_add_"):
            await self._add_to_cart(query, data, user_id)
        elif data.startswith("fav_remove_"):
            await self._remove_from_cart(query, data, user_id)
        else:
            await query.answer("❌ Невідома команда")
    
    # --- ЛОГІКА ДОДАВАННЯ В КОШИК ---
    
    async def _add_to_cart(self, query, data, user_id):
        """Додати улюблену страву до кошика"""
        item_id = data.replace("fav_add_", "")
        
        # Знаходимо страву
        favorites = self.db.get_user_favorites(user_id)
        favorite_item = next((f for f in favorites if f.get('id') == item_id), None)
        
        if not favorite_item:
            await query.answer("❌ Страва не знайдена", show_alert=True)
            # Оновлюємо меню, бо можливо дані застаріли
            await self.show_favorites_menu(query.message, is_update=True)
            return
        
        # Додаємо до кошика
        cart = self.cart.get_user_cart(user_id)
        cart_key = f"fav_{item_id}"
        
        if cart_key in cart:
            cart[cart_key]["quantity"] += 1
        else:
            cart[cart_key] = {
                "name": favorite_item['name'],
                "price": favorite_item.get('price', 0),
                "quantity": 1
            }
        
        await query.answer(f"➕ {favorite_item['name']} додано!")
        # Оновлюємо ТІЛЬКИ кнопки (без нового повідомлення)
        await self.show_favorites_menu(query.message, is_update=True)

    async def _remove_from_cart(self, query, data, user_id):
        """Зменшити кількість або видалити з кошика"""
        item_id = data.replace("fav_remove_", "")
        
        cart = self.cart.get_user_cart(user_id)
        cart_key = f"fav_{item_id}"
        
        if cart_key in cart:
            if cart[cart_key]["quantity"] > 1:
                cart[cart_key]["quantity"] -= 1
                await query.answer("➖ Кількість зменшено")
            else:
                del cart[cart_key]
                await query.answer("🗑 Видалено з кошика")
        
        # Оновлюємо кнопки
        await self.show_favorites_menu(query.message, is_update=True)

    async def _add_all_to_cart(self, query, user_id):
        favorites = self.db.get_user_favorites(user_id)
        if not favorites:
            await query.answer("❌ Порожньо", show_alert=True)
            return
        
        cart = self.cart.get_user_cart(user_id)
        count = 0
        for fav in favorites:
            item_id = fav.get('id')
            if item_id:
                cart_key = f"fav_{item_id}"
                if cart_key in cart:
                    cart[cart_key]["quantity"] += 1
                else:
                    cart[cart_key] = {
                        "name": fav['name'],
                        "price": fav.get('price', 0),
                        "quantity": 1
                    }
                count += 1
        
        await query.answer(f"✅ Додано {count} страв!", show_alert=True)
        await self.show_favorites_menu(query.message, is_update=True)

    async def _clear_favorites(self, query, user_id):
        self.db.clear_user_favorites(user_id)
        await query.answer("🗑 Очищено!")
        await self.show_favorites_menu(query.message, is_update=True)

    # --- ЛОГІКА ВИБОРУ СТРАВ ДЛЯ ЗБЕРЕЖЕННЯ ---

    async def _update_selection_message(self, message_obj, user_id, is_new=False):
        """Оновити повідомлення з вибором (галочки)"""
        if user_id not in self.user_selections:
            return
        
        items = self.user_selections[user_id]['items']
        selected = self.user_selections[user_id]['selected']
        
        keyboard = []
        for item in items[:15]:
            is_selected = item['id'] in selected
            emoji = "✅" if is_selected else "⬜️"
            keyboard.append([
                InlineKeyboardButton(f"{emoji} {item['name']}", 
                                   callback_data=f"fav_select_{item['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("✅ Вибрати всі", callback_data="fav_select_all"),
            InlineKeyboardButton("⬜️ Зняти всі", callback_data="fav_deselect_all")
        ])
        keyboard.append([
            InlineKeyboardButton("💾 ЗБЕРЕГТИ", callback_data="fav_save"),
            InlineKeyboardButton("❌ Скасувати", callback_data="fav_cancel")
        ])
        
        text = (f"❤️ <b>Оберіть страви для збереження:</b>\n\n"
                f"Обрано: {len(selected)} з {len(items)}")
        
        if is_new:
            await message_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            try:
                # message_obj тут це query
                await message_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            except:
                pass

    async def _handle_selection(self, query, data, user_id):
        await query.answer()
        item_id = data.replace("fav_select_", "")
        selected = self.user_selections[user_id]['selected']
        
        if item_id in selected:
            selected.remove(item_id)
        else:
            selected.add(item_id)
        await self._update_selection_message(query, user_id)

    async def _select_all(self, query, user_id):
        await query.answer()
        items = self.user_selections[user_id]['items']
        self.user_selections[user_id]['selected'] = {item['id'] for item in items}
        await self._update_selection_message(query, user_id)

    async def _deselect_all(self, query, user_id):
        await query.answer()
        self.user_selections[user_id]['selected'] = set()
        await self._update_selection_message(query, user_id)

    async def _cancel_selection(self, query, user_id):
        await query.answer("❌ Скасовано")
        if user_id in self.user_selections:
            del self.user_selections[user_id]
        await query.message.delete()

    async def _save_favorites(self, query, user_id):
        if user_id not in self.user_selections:
            await query.answer("❌ Помилка сесії")
            return
            
        selected = self.user_selections[user_id]['selected']
        items = self.user_selections[user_id]['items']
        
        if not selected:
            await query.answer("⚠️ Ви нічого не вибрали!", show_alert=True)
            return
            
        count = 0
        for item in items:
            if item['id'] in selected:
                if self.db.add_user_favorite(user_id, item):
                    count += 1
        
        del self.user_selections[user_id]
        await query.answer(f"✅ Збережено {count} страв!", show_alert=True)
        
        # Повертаємось до меню улюблених
        await self.show_favorites_menu(query.message, is_update=True)
    
    async def debug_favorites(self, message):
        pass # Залиште порожнім або видаліть
    
    async def check_favorites_debug(self, message):
        pass