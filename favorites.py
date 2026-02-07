import hashlib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

class Favorites:
    def __init__(self, database, cart):
        self.db = database
        self.cart = cart
        self.user_selections = {}
    
    def _generate_short_id(self, item_name):
        """Генерує короткий ID для технічних потреб"""
        return hashlib.md5(item_name.encode('utf-8')).hexdigest()[:10]

    async def show_favorites_menu(self, message_or_query, is_callback=False):
        """
        Показує меню улюблених.
        is_callback=True означає, що функцію викликано після натискання кнопки.
        """
        # 1. ПРАВИЛЬНО ВИЗНАЧАЄМО USER ID
        if is_callback:
            # Якщо це клік по кнопці, ID беремо з query.from_user
            user_id = message_or_query.from_user.id
            message = message_or_query.message
        else:
            # Якщо це команда /favorites або текст, ID з message.from_user
            user_id = message_or_query.from_user.id
            message = message_or_query
            
        # 2. Отримуємо улюблені страви з бази
        favorites = self.db.get_user_favorites(user_id)
        
        # Навігація (показуємо тільки якщо це нове повідомлення, не редагування)
        if not is_callback:
            nav_keyboard = [
                [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
                [KeyboardButton("🧾 Чек"), KeyboardButton("🔙 Головне меню")]
            ]
            await message.reply_text(
                "Оберіть дію:",
                reply_markup=ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)
            )
        
        # Перевірка на порожнє улюблене
        if not favorites:
            text = (
                "❤️ <b>УЛЮБЛЕНІ СТРАВИ</b>\n\n"
                "Тут поки порожньо! Додайте страви через '🧾 Чек' після замовлення."
            )
            if is_callback:
                try:
                    await message.edit_text(text, parse_mode="HTML")
                except:
                    pass
            else:
                await message.reply_text(text, parse_mode="HTML")
            return
        
        # Генеруємо кнопки
        reply_markup = self._build_favorites_keyboard(user_id, favorites)
        
        text = "❤️ <b>ВАШІ УЛЮБЛЕНІ СТРАВИ</b>\n👇 Натискайте на страви, щоб додати їх до кошика:"

        if is_callback:
            try:
                # Оновлюємо існуюче повідомлення
                await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
            except Exception:
                # Якщо текст не змінився (тільки цифри), Telegram може видати помилку,
                # тому спробуємо оновити тільки кнопки
                try:
                    await message.edit_reply_markup(reply_markup=reply_markup)
                except:
                    pass
        else:
            await message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    def _build_favorites_keyboard(self, user_id, favorites):
        """Будує клавіатуру, де кнопки показують кількість в кошику"""
        user_cart = self.cart.get_user_cart(user_id)
        keyboard = []
        
        for fav in favorites:
            item_id = fav.get('id', '')
            item_name = fav.get('name', 'Страва')
            
            if not item_id:
                continue
            
            # Перевіряємо кількість цієї страви в кошику
            quantity = 0
            cart_key = f"fav_{item_id}"
            
            if cart_key in user_cart:
                quantity = user_cart[cart_key]['quantity']
            
            # --- ЛОГІКА КНОПОК ---
            if quantity > 0:
                # Емодзі цифри
                emoji_numbers = {
                    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
                    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
                }
                qty_text = emoji_numbers.get(quantity, f"{quantity} шт.")
                
                # Кнопка "Мінус"
                btn_minus = InlineKeyboardButton("➖", callback_data=f"fav_remove_{item_id}")
                
                # Кнопка "Плюс" (відображає кількість)
                btn_main = InlineKeyboardButton(f"{qty_text} {item_name}", callback_data=f"fav_add_{item_id}")
                
                keyboard.append([btn_minus, btn_main])
            else:
                # Звичайна кнопка "Додати"
                btn_add = InlineKeyboardButton(f"➕ {item_name}", callback_data=f"fav_add_{item_id}")
                keyboard.append([btn_add])
        
        # Кнопки управління
        if len(favorites) > 1:
             keyboard.append([InlineKeyboardButton("🛒 Додати ВСІ до кошика", callback_data="fav_add_all")])
        
        keyboard.append([InlineKeyboardButton("🗑 Видалити все з улюблених", callback_data="fav_clear")])
        
        return InlineKeyboardMarkup(keyboard)

    # --- ОБРОБКА НАТИСКАНЬ ---

    async def handle_favorites_callback(self, query, data, user_id):
        """Маршрутизатор callback-запитів"""
        
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
            await query.answer("❌ Невідома дія")

    async def _add_to_cart(self, query, data, user_id):
        """Додає +1 до страви і оновлює кнопки"""
        item_id = data.replace("fav_add_", "")
        
        favorites = self.db.get_user_favorites(user_id)
        favorite_item = next((f for f in favorites if f.get('id') == item_id), None)
        
        if not favorite_item:
            await query.answer("❌ Помилка: страва не знайдена в базі", show_alert=True)
            return
        
        # Додаємо в кошик
        cart = self.cart.get_user_cart(user_id)
        cart_key = f"fav_{item_id}"
        
        if cart_key in cart:
            cart[cart_key]["quantity"] += 1
            new_qty = cart[cart_key]["quantity"]
            await query.answer(f"Додано ще одну! ({new_qty})")
        else:
            cart[cart_key] = {
                "name": favorite_item['name'],
                "price": favorite_item.get('price', 0),
                "quantity": 1
            }
            await query.answer("✅ Додано до кошика!")
        
        # Оновлюємо вигляд кнопок (цифри зміняться), передаємо query як об'єкт
        await self.show_favorites_menu(query, is_callback=True)

    async def _remove_from_cart(self, query, data, user_id):
        """Зменшує кількість (-1)"""
        item_id = data.replace("fav_remove_", "")
        
        cart = self.cart.get_user_cart(user_id)
        cart_key = f"fav_{item_id}"
        
        if cart_key in cart:
            if cart[cart_key]["quantity"] > 1:
                cart[cart_key]["quantity"] -= 1
                await query.answer("➖ Кількість зменшено")
            else:
                del cart[cart_key]
                await query.answer("🗑 Прибрано з кошика")
        
        # Оновлюємо кнопки
        await self.show_favorites_menu(query, is_callback=True)

    async def _add_all_to_cart(self, query, user_id):
        """Додає всі страви"""
        favorites = self.db.get_user_favorites(user_id)
        cart = self.cart.get_user_cart(user_id)
        
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
        
        await query.answer("✅ Всі улюблені страви додано!")
        await self.show_favorites_menu(query, is_callback=True)

    async def _clear_favorites(self, query, user_id):
        """Очищає список улюблених"""
        self.db.clear_user_favorites(user_id)
        await query.answer("🗑 Список улюблених очищено!")
        await self.show_favorites_menu(query, is_callback=True)

    # --- ЗБЕРЕЖЕННЯ З ЧЕКУ (БЕЗ ЗМІН) ---

    async def start_add_favorites(self, message, order_ids):
        user_id = message.from_user.id
        data = self.db.load_data()
        unique_items = []
        seen_names = set()
        
        for order_id in order_ids:
            order = data.get("orders", {}).get(order_id)
            if order and str(order.get("user_id")) == str(user_id):
                for item in order.get("items", {}).values():
                    item_name = item.get("name", "")
                    if item_name and item_name not in seen_names:
                        seen_names.add(item_name)
                        short_id = self._generate_short_id(item_name)
                        unique_items.append({
                            'id': short_id, 
                            'name': item_name,
                            'price': item.get("price", 0),
                            'quantity': 1 
                        })
        
        if not unique_items:
            await message.reply_text("❌ Не знайдено страв.")
            return
        
        self.user_selections[user_id] = {'items': unique_items, 'selected': set()}
        await self._update_selection_message(message, user_id, is_new=True)

    async def _update_selection_message(self, message_obj, user_id, is_new=False):
        if user_id not in self.user_selections: return
        items = self.user_selections[user_id]['items']
        selected = self.user_selections[user_id]['selected']
        
        keyboard = []
        for item in items[:15]:
            is_selected = item['id'] in selected
            emoji = "✅" if is_selected else "⬜️"
            keyboard.append([InlineKeyboardButton(f"{emoji} {item['name']}", callback_data=f"fav_select_{item['id']}")])
        
        keyboard.append([
            InlineKeyboardButton("✅ Всі", callback_data="fav_select_all"),
            InlineKeyboardButton("⬜️ Жодної", callback_data="fav_deselect_all")
        ])
        keyboard.append([
            InlineKeyboardButton("💾 ЗБЕРЕГТИ", callback_data="fav_save"),
            InlineKeyboardButton("❌ Скасувати", callback_data="fav_cancel")
        ])
        
        text = f"❤️ <b>Оберіть страви для збереження:</b>\nОбрано: {len(selected)}"
        
        if is_new:
            await message_obj.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        else:
            try:
                await message_obj.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
            except: pass

    async def _handle_selection(self, query, data, user_id):
        await query.answer()
        item_id = data.replace("fav_select_", "")
        selected = self.user_selections[user_id]['selected']
        if item_id in selected: selected.remove(item_id)
        else: selected.add(item_id)
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
        if user_id in self.user_selections: del self.user_selections[user_id]
        await query.message.delete()

    async def _save_favorites(self, query, user_id):
        if user_id not in self.user_selections: return
        selected = self.user_selections[user_id]['selected']
        items = self.user_selections[user_id]['items']
        
        if not selected:
            await query.answer("⚠️ Оберіть щось!", show_alert=True)
            return
            
        count = 0
        for item in items:
            if item['id'] in selected:
                if self.db.add_user_favorite(user_id, item): count += 1
        
        del self.user_selections[user_id]
        await query.answer(f"✅ Збережено {count} страв!", show_alert=True)
    
    async def debug_favorites(self, message): pass
    async def check_favorites_debug(self, message): pass
