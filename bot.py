import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import Database
from menu import Menu
from cart import Cart
from admin import Admin
from favorites import Favorites



# Встав сюди свій токен
BOT_TOKEN = "7292645737:AAEDy6Zz4JFolSOm_cN7rI4Wd9W5yjpkn2I"
ADMIN_PASSWORD = "123"

class FoodOrderBot:
    def __init__(self):
        self.db = Database()
        self.cart = Cart(self.db)
        self.menu = Menu(self.db, self.cart)  # Додаємо cart
        self.admin = Admin(self.db, ADMIN_PASSWORD)
        self.favorites = Favorites(self.db, self.cart)
        self.user_states = {}
        self.user_order_types = {}
        self.user_current_check = {}

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        context.user_data['order_type'] = None
        self.user_order_types[user_id] = None
        keyboard = [[KeyboardButton("🚗 Доставка"), KeyboardButton("🏠 В закладі")]]
        await update.message.reply_text(
            "🍕 <b>Вітаємо у FOOD ORDER PRO!</b>\nДе ви плануєте їсти?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode="HTML"
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        text = update.message.text
        state = self.user_states.get(user_id)
        order_type = context.user_data.get('order_type')

        # --- 1. ВИБІР РЕЖИМУ ---
        if text in ["🚗 Доставка", "🏠 В закладі"]:
            context.user_data['order_type'] = text
            self.user_order_types[user_id] = text
            
            kb = [
                [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
                [KeyboardButton("🧾 Чек"), KeyboardButton("❤️ Улюблене")],
                [KeyboardButton("🔙 Головне меню")]
            ]
            await update.message.reply_text(f"Ви обрали: <b>{text}</b>", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode="HTML")
            await self.menu.show_categories(update.message)
            return

        # --- 2. НАВІГАЦІЯ ---
        if text == "🔙 Головне меню":
            await self.start(update, context)
            return
            
        elif text in ["🍽 Меню", "🔙 Назад до категорій", "🚗 Додати ще страви"]:
            await self.menu.show_categories(update.message)
            
        elif text == "🛒 Кошик" or text == "🔙 Кошик":
            await self.cart.show_cart(update.message, order_type)
            
        elif text == "🗑 Очистити кошик":
            await self.cart.clear_cart(update.message)
            
        elif text == "🧾 Чек":
            current_order_type = self.user_order_types.get(user_id, order_type)
            # Отримуємо ID активних замовлень і зберігаємо їх
            active_order_ids = await self.cart.show_active_check(update.message, current_order_type)
            if active_order_ids:
                self.user_current_check[user_id] = active_order_ids
                
                # Показуємо кнопку для додавання в улюблені
                nav_keyboard = [
                    [KeyboardButton("❤️ Додати в улюблене")],
                    [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
                    [KeyboardButton("🔙 Назад")]
                ]
                reply_markup = ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    "📌 <i>Хочете зберегти страви з цього чеку в улюблені?</i>",
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            
        elif text == "❤️ Улюблене":
            await self.favorites.show_favorites_menu(update.message)

        # --- 3. ПРОЦЕС ЗАМОВЛЕННЯ ---
        elif text == "✅ Підтвердити замовлення":
            if order_type == "🏠 В закладі":
                self.user_states[user_id] = "waiting_table_number"
            else:
                self.user_states[user_id] = "waiting_address"
            await self.cart.request_info(update.message, order_type)

        # --- 4. ДОДАВАННЯ ДО УЛЮБЛЕНИХ ---
        elif text == "❤️ Додати в улюблене":
            if user_id in self.user_current_check:
                order_ids = self.user_current_check[user_id]
                await self.favorites.start_add_favorites(update.message, order_ids)
            else:
                await update.message.reply_text("❌ Спочатку перегляньте ваш чек в розділі '🧾 Чек'.")

        elif text == "🔙 Назад":
            current_order_type = self.user_order_types.get(user_id, order_type)
            kb = [
                [KeyboardButton("🍽 Меню"), KeyboardButton("🛒 Кошик")],
                [KeyboardButton("🧾 Чек"), KeyboardButton("❤️ Улюблене")],
                [KeyboardButton("🔙 Головне меню")]
            ]
            await update.message.reply_text(
                f"🔙 Повернення до меню",
                reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True),
                parse_mode="HTML"
            )

        # --- 5. ОБРОБКА ВВЕДЕННЯ ДАНИХ ---
        elif state == "waiting_table_number":
            if text.isdigit():
                await self.cart.confirm_order(update.message, f"Столик №{text}", order_type)
                self.user_states[user_id] = None
            else:
                await update.message.reply_text("❌ Будь ласка, введіть тільки цифру (номер столика):")

        elif state == "waiting_address":
            await self.cart.confirm_order(update.message, text, order_type)
            self.user_states[user_id] = None

        elif state == "waiting_admin_password":
            if self.admin.verify_password(text):
                self.admin.add_admin_session(user_id)
                self.user_states[user_id] = None
                await self.admin.show_admin_panel(update.message)
            else:
                await update.message.reply_text("❌ Невірний пароль!")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        order_type = context.user_data.get('order_type', "🚗 Доставка")

        if data.startswith("category_"):
            await self.menu.show_category_items(query, data.split("_")[1], order_type)
        elif data.startswith("add_to_cart_"):
            cat, item_id = data.split("_")[3].split("-")
            await self.cart.add_to_cart(query, cat, item_id)
        elif data.startswith("pay_"):
            if data.startswith("pay_all_"):
                orders_str = data.replace("pay_all_", "")
                order_ids = orders_str.split("_")
                await self.cart.process_payment_all(query, order_ids)
            else:
                order_id = data.replace("pay_", "")
                await self.cart.process_payment(query, order_id)
        elif data.startswith("fav_"):
            await self.favorites.handle_favorites_callback(query, data, user_id)
        elif data.startswith("admin_"):
            if self.admin.is_admin(user_id):
                await self.admin.handle_callback(query, data, user_id, self.user_states)

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user_states[update.message.from_user.id] = "waiting_admin_password"
        await update.message.reply_text("🔐 Пароль:")
    
    async def debug_fav(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для дебагу улюблених"""
        await self.favorites.debug_favorites(update.message)


def main():
    bot = FoodOrderBot()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("admin", bot.admin_command))
    app.add_handler(CallbackQueryHandler(bot.handle_callback))
    app.add_handler(CommandHandler("debugfav", bot.debug_fav))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    app.add_handler(CommandHandler("debugfav", bot.debug_fav))
    
    
    print("Бот запущено...")
    app.run_polling()

if __name__ == "__main__":
    main()