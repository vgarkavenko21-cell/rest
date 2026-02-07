from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
import os

class Menu:
    def __init__(self, database, cart):  # Додаємо cart
        self.db = database
        self.cart = cart  # Зберігаємо посилання на cart
    
    async def show_categories(self, message):
        categories = self.db.get_categories()
        keyboard = []
        for cat_id, cat_data in categories.items():
            keyboard.append([InlineKeyboardButton(cat_data["name"], callback_data=f"category_{cat_id}")])
        
        await message.reply_text("🍽 <b>МЕНЮ</b>\nОберіть категорію:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    
    async def show_category_items(self, query, category, order_type="🚗 Доставка"):
        cat_data = self.db.get_category(category)
        items = self.db.get_category_items(category)
        
        # Кнопки навігації
        nav_keyboard = [
            [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
            [KeyboardButton("🧾 Чек"), KeyboardButton("❤️ Улюблене")],
            [KeyboardButton("🔙 Головне меню")]
        ]
            
        await query.message.reply_text(
            f"📂 Категорія: <b>{cat_data['name']}</b>",
            reply_markup=ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True),
            parse_mode="HTML"
        )
        
        if not items:
            await query.message.reply_text("Тут поки порожньо 😔")
            return

        # Отримуємо поточний кошик користувача
        user_id = query.from_user.id
        # Треба отримати доступ до cart, додамо його як атрибут
        # Якщо немає доступу до cart, створимо простий спосіб отримати кількість
        cart_count = {}
        # Припустимо, що у нас є доступ до cart через query.bot
        try:
            # Якщо є доступ до бота
            if hasattr(query, 'bot') and hasattr(query.bot, 'food_order_bot'):
                cart = query.bot.food_order_bot.cart.get_user_cart(user_id)
                for cart_key, cart_item in cart.items():
                    # cart_key формат: "category_item_id"
                    if cart_key.startswith(f"{category}_"):
                        # Знаходимо item_id з ключа
                        item_id_in_cart = cart_key.split('_')[1]
                        if item_id_in_cart in items:
                            cart_count[item_id_in_cart] = cart_item['quantity']
        except:
            pass

        for item_id, item in items.items():
            text = f"<b>{item['name']}</b>\n{item.get('description', '')}\n💸 <b>{item['price']}₴</b>"
            
            # Отримуємо кількість цієї страви в кошику
            quantity_in_cart = cart_count.get(item_id, 0)
            
            # Створюємо текст кнопки з смайликом-лічильником
            if quantity_in_cart > 0:
                # Емодзі для різних чисел
                emoji_numbers = {
                    1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣",
                    6: "6️⃣", 7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
                }
                if quantity_in_cart <= 10:
                    counter = emoji_numbers[quantity_in_cart]
                else:
                    counter = f"{quantity_in_cart}️⃣"
                
                button_text = f"🛒 {counter} В кошику"
            else:
                button_text = "🛒 В кошик"
            
            kb = [[InlineKeyboardButton(button_text, callback_data=f"add_to_cart_{category}-{item_id}")]]
            
            if os.path.exists(item.get('image', '')):
                try:
                    with open(item['image'], 'rb') as photo:
                        await query.message.reply_photo(photo, caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
                except:
                    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
            else:
                await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")