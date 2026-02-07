from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

class Favorites:
    def __init__(self, database, cart):
        self.db = database
        self.cart = cart
        self.user_selections = {}
    
    async def show_favorites_menu(self, message):
        """Показуємо меню улюблених страв"""
        user_id = message.from_user.id
        
        # Отримуємо улюблені страви
        favorites = self.db.get_user_favorites(user_id)
        
        # Навігаційна клавіатура - показуємо ЗАВЖДИ
        nav_keyboard = [
            [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
            [KeyboardButton("🧾 Чек"), KeyboardButton("🔙 Головне меню")]
        ]
        
        # Перевіряємо чи є улюблені
        if not favorites:
            reply_markup = ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)
            await query.answer(f"🔥 СУПЕР! {favorite_item['name']} додано до кошика!", show_alert=True)
        
        # Отримуємо кошик користувача
        user_cart = self.cart.get_user_cart(user_id)
        
        # Створюємо кнопки
        keyboard = []
        
        for fav in favorites[:10]:  # Обмежуємо до 10 страв
            item_id = fav.get('id', '')
            item_name = fav.get('name', 'Невідома страва')
            
            if not item_id:
                continue
            
            # Перевіряємо, чи ця страва вже в кошику
            is_in_cart = False
            quantity = 0
            
            # Ключ для улюблених страв в кошику
            cart_key = f"fav_{item_id}"
            if cart_key in user_cart:
                is_in_cart = True
                quantity = user_cart[cart_key]['quantity']
            
            # Створюємо текст кнопки
            if is_in_cart and quantity > 0:
                # Емодзі-лічильники
                emoji_numbers = {
                    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
                    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
                }
                
                if quantity <= 10:
                    counter = emoji_numbers[quantity]
                else:
                    counter = f"{quantity}🛒"
                
                button_text = f"{counter} {item_name}"
                callback_data = f"fav_remove_{item_id}"
            else:
                button_text = f"➕ {item_name}"
                callback_data = f"fav_add_{item_id}"
            
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        # Кнопка для додавання всіх страв
        if len(favorites) > 1:
            keyboard.append([
                InlineKeyboardButton("🛒 Додати всі до кошика", callback_data="fav_add_all")
            ])
        
        # Кнопка очищення улюблених
        keyboard.append([
            InlineKeyboardButton("🗑 Очистити улюблені", callback_data="fav_clear")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Спершу показуємо навігаційну клавіатуру
        await message.reply_text(
            "Оберіть дію:",
            reply_markup=ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)
        )
        
        # Потім показуємо улюблені страви
        await message.reply_text(
            "❤️ <b>ВАШІ УЛЮБЛЕНІ СТРАВИ</b>",
            reply_markup=reply_markup,
            parse_mode="HTML"
        )
    
    async def start_add_favorites(self, message, order_ids):
        """Початок додавання страв в улюблені з чеку"""
        user_id = message.from_user.id
        
        # Отримуємо всі унікальні страви з замовлень
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
                        unique_items.append({
                            'id': f"fav_{order_id}_{item_name}",
                            'name': item_name,
                            'price': item.get("price", 0),
                            'quantity': item.get("quantity", 1)
                        })
        
        if not unique_items:
            await message.reply_text("❌ У цьому чеку немає страв для додавання.")
            return
        
        # Зберігаємо для подальшої обробки
        self.user_selections[user_id] = {
            'items': unique_items,
            'selected': set()
        }
        
        # Створюємо інлайн-клавіатуру для вибору
        keyboard = []
        
        for item in unique_items[:15]:  # Обмежуємо до 15
            keyboard.append([
                InlineKeyboardButton(f"☐ {item['name']}", 
                                   callback_data=f"fav_select_{item['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("✅ Вибрати всі", callback_data="fav_select_all"),
            InlineKeyboardButton("☐ Скасувати всі", callback_data="fav_deselect_all")
        ])
        
        keyboard.append([
            InlineKeyboardButton("💾 Зберегти вибір", callback_data="fav_save"),
            InlineKeyboardButton("❌ Відмінити", callback_data="fav_cancel")
        ])
        
        await message.reply_text(
            "❤️ <b>Оберіть страви, які вам сподобались:</b>\n\n"
            "Вони будуть збережені в розділі 'Улюблене' для швидкого повторення замовлення.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    async def handle_favorites_callback(self, query, data, user_id):
        """Обробка всіх callback для улюблених"""
        await query.answer()
        
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
            # Додаємо страви до кошика
            await self._add_to_cart(query, data, user_id)
        elif data.startswith("fav_remove_"):
            # Видаляємо з кошика
            await self._remove_from_cart(query, data, user_id)
        else:
            await query.answer("❌ Невідома команда", show_alert=True)
    
    async def _handle_selection(self, query, data, user_id):
        """Обробка вибору окремої страви"""
        item_id = data.replace("fav_select_", "")
        
        if user_id not in self.user_selections:
            self.user_selections[user_id] = {'selected': set()}
        
        selected = self.user_selections[user_id]['selected']
        
        if item_id in selected:
            selected.remove(item_id)
        else:
            selected.add(item_id)
        
        await self._update_selection_message(query, user_id)
    
    async def _select_all(self, query, user_id):
        """Вибрати всі страви"""
        if user_id in self.user_selections:
            items = self.user_selections[user_id]['items']
            self.user_selections[user_id]['selected'] = {item['id'] for item in items}
            await self._update_selection_message(query, user_id)
    
    async def _deselect_all(self, query, user_id):
        """Скасувати вибір всіх страв"""
        if user_id in self.user_selections:
            self.user_selections[user_id]['selected'] = set()
            await self._update_selection_message(query, user_id)
    
    async def _update_selection_message(self, query, user_id):
        """Оновити повідомлення з вибором"""
        if user_id not in self.user_selections:
            return
        
        items = self.user_selections[user_id]['items']
        selected = self.user_selections[user_id]['selected']
        
        keyboard = []
        
        for item in items[:15]:
            is_selected = item['id'] in selected
            emoji = "✅" if is_selected else "☐"
            keyboard.append([
                InlineKeyboardButton(f"{emoji} {item['name']}", 
                                   callback_data=f"fav_select_{item['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("✅ Вибрати всі", callback_data="fav_select_all"),
            InlineKeyboardButton("☐ Скасувати всі", callback_data="fav_deselect_all")
        ])
        
        keyboard.append([
            InlineKeyboardButton("💾 Зберегти вибір", callback_data="fav_save"),
            InlineKeyboardButton("❌ Відмінити", callback_data="fav_cancel")
        ])
        
        try:
            await query.edit_message_text(
                f"❤️ <b>Оберіть страви, які вам сподобались:</b>\n\n"
                f"✅ Вибрано: {len(selected)} з {len(items)} страв",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
        except:
            pass
    
    async def _save_favorites(self, query, user_id):
        """Зберегти вибрані страви в улюблені"""
        if user_id not in self.user_selections:
            await query.answer("❌ Немає вибраних страв", show_alert=True)
            return
        
        selected = self.user_selections[user_id]['selected']
        items = self.user_selections[user_id]['items']
        
        if not selected:
            await query.answer("❌ Ви не вибрали жодної страви", show_alert=True)
            return
        
        saved_count = 0
        for item_id in selected:
            for item in items:
                if item['id'] == item_id:
                    # Додаємо в улюблені
                    success = self.db.add_user_favorite(user_id, item)
                    if success:
                        saved_count += 1
                    break
        
        # Очищаємо тимчасові дані
        if user_id in self.user_selections:
            del self.user_selections[user_id]
        
        await query.answer(f"✅ Збережено {saved_count} страв", show_alert=True)
        
        # Повертаємо в головне меню
        keyboard = [
            [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
            [KeyboardButton("🧾 Чек"), KeyboardButton("❤️ Улюблене")],
            [KeyboardButton("🔙 Головне меню")]
        ]
        
        await query.edit_message_text(
            f"✅ <b>Улюблені страви збережено!</b>\n\n"
            f"Додано {saved_count} страв в розділ 'Улюблене'.",
            parse_mode="HTML"
        )
        
        await query.message.reply_text(
            "🔙 Повернення до головного меню",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    
    async def _cancel_selection(self, query, user_id):
        """Скасувати вибір"""
        if user_id in self.user_selections:
            del self.user_selections[user_id]
        
        await query.edit_message_text("❌ Додавання в улюблені скасовано.")
    
    async def _add_to_cart(self, query, data, user_id):
        """Додати улюблену страву до кошика"""
        item_id = data.replace("fav_add_", "")
        
        # Знаходимо страву в улюблених
        favorites = self.db.get_user_favorites(user_id)
        favorite_item = None
        
        for fav in favorites:
            if fav.get('id') == item_id:
                favorite_item = fav
                break
        
        if not favorite_item:
            await query.answer("❌ Страва не знайдена", show_alert=True)
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
        
        await query.answer(f"✅ {favorite_item['name']} додано до кошика!", show_alert=True)
        await self.show_favorites_menu(query.message)
    
    async def _remove_from_cart(self, query, data, user_id):
        """Видалити страву з кошика"""
        item_id = data.replace("fav_remove_", "")
        
        cart = self.cart.get_user_cart(user_id)
        cart_key = f"fav_{item_id}"
        
        if cart_key in cart:
            if cart[cart_key]["quantity"] > 1:
                cart[cart_key]["quantity"] -= 1
                action = "зменшено"
            else:
                del cart[cart_key]
                action = "видалено"
            
            # Знаходимо назву страви
            favorites = self.db.get_user_favorites(user_id)
            item_name = "Страва"
            for fav in favorites:
                if fav.get('id') == item_id:
                    item_name = fav['name']
                    break
            
            await query.answer(f"✅ {item_name} {action} з кошика", show_alert=True)
        else:
            await query.answer("❌ Страва не знайдена в кошику", show_alert=True)
        
        await self.show_favorites_menu(query.message)
    
    async def _add_all_to_cart(self, query, user_id):
        """Додати всі улюблені страви до кошика"""
        favorites = self.db.get_user_favorites(user_id)
        
        if not favorites:
            await query.answer("❌ Немає улюблених страв", show_alert=True)
            return
        
        cart = self.cart.get_user_cart(user_id)
        added_count = 0
        
        for fav in favorites:
            item_id = fav.get('id', '')
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
                
                added_count += 1
        
        await query.answer(f"✅ Додано {added_count} страв до кошика!", show_alert=True)
        await self.show_favorites_menu(query.message)
    
    async def _remove_favorite(self, query, data, user_id):
        """Видалити страву з улюблених"""
        item_id = data.replace("fav_remove_", "")
        
        if self.db.remove_user_favorite(user_id, item_id):
            await query.answer("✅ Страва видалена з улюблених", show_alert=True)
            await self.show_favorites_menu(query.message)
        else:
            await query.answer("❌ Помилка при видаленні", show_alert=True)
    
    async def _clear_favorites(self, query, user_id):
        """Очистити всі улюблені"""
        favorites = self.db.get_user_favorites(user_id)
        
        if not favorites:
            await query.answer("❌ Немає що очищати", show_alert=True)
            return
        
        # Видаляємо кожну страву
        for fav in favorites:
            item_id = fav.get('id', '')
            if item_id:
                self.db.remove_user_favorite(user_id, item_id)
        
        await query.answer("✅ Всі улюблені страви очищено", show_alert=True)
        await query.edit_message_text("🗑️ Всі улюблені страви видалено.")

    async def debug_favorites(self, message):
        """Детальна інформація про улюблені для дебагу"""
        user_id = message.from_user.id
        favorites = self.db.get_user_favorites(user_id)
        
        debug_text = f"🔍 ДЕБАГ Улюблених для user_id={user_id}:\n"
        debug_text += f"Кількість улюблених: {len(favorites) if favorites else 0}\n"
        
        if favorites:
            debug_text += "\nСписок улюблених:\n"
            for i, fav in enumerate(favorites, 1):
                debug_text += f"{i}. ID: {fav.get('id', 'немає')}\n"
                debug_text += f"   Назва: {fav.get('name', 'Без назви')}\n"
                debug_text += f"   Ціна: {fav.get('price', 0)}₴\n"
        
        await message.reply_text(debug_text)
