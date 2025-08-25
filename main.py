
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

BOT_TOKEN = os.getenv("BOT_TOKEN")  # получишь у @BotFather
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # свой Telegram ID (необязательно)

if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не установлена")

bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage())

# === Тарифы (разовые) ===
RATES = {
    "standard": {"name": "Стандартная уборка", "per_m2": 9000, "min": 350000, "needs_area": True},
    "general": {"name": "Генеральная уборка", "per_m2": 12000, "min": 700000, "needs_area": True},
    "post_renovation": {"name": "Уборка после ремонта", "per_m2": 35000, "min": 2000000, "needs_area": True},
    "clean_start": {"name": "Чистый старт", "per_m2": 20000, "min": 1100000, "needs_area": True},
    "kitchen_bath_standard": {"name": "Кухня + санузел (стандарт)", "fixed": 360000, "needs_area": False},
    "kitchen_bath_general": {"name": "Кухня + санузел (генеральная)", "fixed": 450000, "needs_area": False},
}

# === Доп. услуги ===
EXTRAS = {
    "windows_90": {"name": "Окна/поверхности (90 000 за ед.)", "type": "per_unit", "price": 90000},
    "windows_110": {"name": "Окна/поверхности (110 000 за ед.)", "type": "per_unit", "price": 110000},
    "walls": {"name": "Стены (270 000 / час)", "type": "per_hour", "price": 270000},
    "staircase": {"name": "Лестница (130 000 за ед.)", "type": "per_unit", "price": 130000},
    "ladder": {"name": "Стремянка (130 000)", "type": "fixed", "price": 130000},
    "laundry": {"name": "Стирка (135 000 за загрузку)", "type": "per_unit", "price": 135000},
    "ironing": {"name": "Глажка (285 000 / час)", "type": "per_hour", "price": 285000},
    "balcony": {"name": "Балкон (135 000 за ед.)", "type": "per_unit", "price": 135000},
    "second_wc": {"name": "Второй санузел (150 000 за ед.)", "type": "per_unit", "price": 150000},
    "organize": {"name": "Разложить вещи (220 000 / час)", "type": "per_hour", "price": 220000},
    "pet_litter": {"name": "Лоток для животных (100 000 за ед.)", "type": "per_unit", "price": 100000},
    "chair": {"name": "Химчистка: стул (100 000)", "type": "per_unit", "price": 100000},
    "armchair": {"name": "Химчистка: кресло (160 000)", "type": "per_unit", "price": 160000},
    "sofa_2": {"name": "Химчистка: диван 2-местный (550 000)", "type": "per_unit", "price": 550000},
    "sofa_3": {"name": "Химчистка: диван 3-местный (630 000)", "type": "per_unit", "price": 630000},
    "sofa_extra": {"name": "Химчистка: доп. место (130 000)", "type": "per_unit", "price": 130000},
    "mattress_1": {"name": "Матрас односпальный (260 000)", "type": "per_unit", "price": 260000},
    "mattress_2": {"name": "Матрас двуспальный (410 000)", "type": "per_unit", "price": 410000},
    "pillow": {"name": "Подушка (60 000)", "type": "per_unit", "price": 60000},
    "blanket": {"name": "Одеяло/плед (350 000)", "type": "per_unit", "price": 350000},
    "carpet": {"name": "Ковер (от 215 000 — уточняется)", "type": "per_unit", "price": 215000},
}

# === Абонементы ===
PLANS = {
    "combo": {
        "name": "Комбо (3 стандартные + 1 генеральная / месяц)",
        "sizes": {60: 2652000, 80: 2808000, 100: 3120000, 120: 3802500},
    },
    "standard_month": {
        "name": "Стандарт (2 стандартные / месяц)",
        "sizes": {60: 972000, 80: 1224000, 100: 1440000, 130: 2152500},
    },
    "cozy": {
        "name": "Уютный график (1 стандартная + 1 генеральная / месяц)",
        "sizes": {60: 1134000, 80: 1428000, 100: 1680000, 130: 2730000},
    },
}

# ===== Состояния FSM =====
class Order(StatesGroup):
    choosing_category = State()
    choosing_tariff = State()
    input_area = State()
    choose_extras = State()
    extras_menu = State()
    extras_value = State()
    gather_name = State()
    gather_phone = State()
    gather_address = State()
    gather_datetime = State()
    gather_comment = State()
    confirm = State()

def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🧹 Разовая уборка", "📅 Абонементы")
    kb.add("➕ Доп. услуги", "💬 Оператор")
    return kb

def tariffs_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Стандартная уборка", "Генеральная уборка")
    kb.add("После ремонта", "Чистый старт")
    kb.add("Кухня+санузел (стандарт)", "Кухня+санузел (генерал.)")
    kb.add("⬅️ Назад")
    return kb

def yes_no_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("Да", "Нет")
    return kb

def extras_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Окна 90k", "Окна 110k", "Стены")
    kb.add("Лестница", "Стремянка", "Стирка", "Глажка")
    kb.add("Балкон", "2-й санузел", "Разложить вещи", "Лоток")
    kb.add("Стул", "Кресло", "Диван 2м", "Диван 3м", "Доп место")
    kb.add("Матрас 1сп", "Матрас 2сп", "Подушка", "Одеяло/плед", "Ковер")
    kb.add("✅ Готово")
    return kb

def plans_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Комбо", "Стандарт (мес.)", "Уютный график")
    kb.add("⬅️ Назад")
    return kb

def sizes_kb(sizes):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    row = []
    for s in sizes:
        row.append(f"{s} кв.м")
        if len(row) == 3:
            kb.add(*row); row = []
    if row:
        kb.add(*row)
    kb.add("⬅️ Назад")
    return kb

def fmt_money(n):
    return f"{n:,}".replace(",", " ")

def order_summary(data):
    lines = []
    lines.append(f"<b>{data.get('service_name','Заказ')}</b>")
    if 'area' in data and data['area']:
        lines.append(f"Площадь: {data['area']} кв.м")
    lines.append("")
    lines.append("<b>Состав заказа:</b>")
    for item in data['items']:
        lines.append(f"• {item['name']}: {fmt_money(item['amount'])} сум")
    lines.append("")
    lines.append(f"<b>Итого: {fmt_money(data['total'])} сум</b>")
    lines.append("")
    if data.get("name"):
        lines.append(f"Клиент: {data['name']}")
    if data.get("phone"):
        lines.append(f"Телефон: {data['phone']}")
    if data.get("address"):
        lines.append(f"Адрес: {data['address']}")
    if data.get("when"):
        lines.append(f"Дата/время: {data['when']}")
    if data.get("comment"):
        lines.append(f"Комментарий: {data['comment']}")
    return "\n".join(lines)

@dp.message_handler(commands=["start"])
async def start(m: types.Message, state: FSMContext):
    await state.finish()
    await m.answer(
        "Добро пожаловать в <b>OneTouch Group</b>!\n"
        "Выберите категорию:", reply_markup=main_menu_kb()
    )
    await Order.choosing_category.set()

@dp.message_handler(lambda msg: msg.text == "💬 Оператор", state="*")
async def operator(m: types.Message, state: FSMContext):
    await m.answer("Напишите ваш вопрос. Менеджер свяжется с вами.", reply_markup=main_menu_kb())

@dp.message_handler(lambda msg: msg.text == "🧹 Разовая уборка", state=Order.choosing_category)
async def choose_tariff(m: types.Message, state: FSMContext):
    await m.answer("Выберите тип уборки:", reply_markup=tariffs_kb())
    await Order.choosing_tariff.set()

@dp.message_handler(lambda msg: msg.text == "📅 Абонементы", state=Order.choosing_category)
async def choose_plan(m: types.Message, state: FSMContext):
    await m.answer("Выберите абонемент:", reply_markup=plans_kb())

@dp.message_handler(lambda msg: msg.text == "⬅️ Назад", state="*")
async def back_to_menu(m: types.Message, state: FSMContext):
    await state.finish()
    await m.answer("Главное меню:", reply_markup=main_menu_kb())
    await Order.choosing_category.set()

# ===== Абонементы =====
@dp.message_handler(lambda msg: msg.text in ["Комбо", "Стандарт (мес.)", "Уютный график"], state="*")
async def plan_sizes(m: types.Message, state: FSMContext):
    mapping = {
        "Комбо": "combo",
        "Стандарт (мес.)": "standard_month",
        "Уютный график": "cozy",
    }
    key = mapping[m.text]
    await state.update_data(plan_key=key, service_name=PLANS[key]["name"])
    sizes = list(PLANS[key]["sizes"].keys())
    await m.answer("Выберите площадь:", reply_markup=sizes_kb(sizes))

@dp.message_handler(lambda msg: msg.text.endswith("кв.м"), state="*")
async def plan_total(m: types.Message, state: FSMContext):
    data = await state.get_data()
    if "plan_key" not in data:
        return
    size = int(m.text.split()[0])
    price = PLANS[data["plan_key"]]["sizes"][size]
    await state.update_data(
        items=[{"name": f"{PLANS[data['plan_key']]['name']} — {size} кв.м", "amount": price}],
        total=price,
        area=size,
    )
    await m.answer(
        f"Стоимость: <b>{fmt_money(price)} сум</b>\n"
        "Оставьте контактный номер телефона:", reply_markup=types.ReplyKeyboardRemove()
    )
    await Order.gather_phone.set()

# ===== Разовая уборка =====
@dp.message_handler(lambda msg: msg.text in [
    "Стандартная уборка", "Генеральная уборка", "После ремонта", "Чистый старт",
    "Кухня+санузел (стандарт)", "Кухня+санузел (генерал.)"
], state=Order.choosing_tariff)
async def selected_tariff(m: types.Message, state: FSMContext):
    mapping = {
        "Стандартная уборка": "standard",
        "Генеральная уборка": "general",
        "После ремонта": "post_renovation",
        "Чистый старт": "clean_start",
        "Кухня+санузел (стандарт)": "kitchen_bath_standard",
        "Кухня+санузел (генерал.)": "kitchen_bath_general",
    }
    tkey = mapping[m.text]
    tariff = RATES[tkey]
    await state.update_data(tariff_key=tkey, service_name=tariff["name"], items=[])
    if tariff.get("needs_area"):
        await m.answer("Введите площадь (в кв.м), например: 60", reply_markup=types.ReplyKeyboardRemove())
        await Order.input_area.set()
    else:
        amount = tariff["fixed"]
        data = await state.get_data()
        data["items"].append({"name": tariff["name"], "amount": amount})
        await state.update_data(items=data["items"], total=amount)
        await m.answer(
            f"Базовая стоимость: <b>{fmt_money(amount)} сум</b>\n"
            "Добавить доп. услуги?", reply_markup=yes_no_kb()
        )
        await Order.choose_extras.set()

@dp.message_handler(lambda msg: msg.text.isdigit(), state=Order.input_area)
async def got_area(m: types.Message, state: FSMContext):
    area = int(m.text)
    data = await state.get_data()
    tariff = RATES[data["tariff_key"]]
    base = area * tariff["per_m2"]
    if base < tariff["min"]:
        base = tariff["min"]
    items = data["items"]
    items.append({"name": f"{tariff['name']} — {area} кв.м", "amount": base})
    await state.update_data(area=area, items=items, total=base)
    await m.answer(
        f"Базовая стоимость: <b>{fmt_money(base)} сум</b>\n"
        "Добавить доп. услуги?", reply_markup=yes_no_kb()
    )
    await Order.choose_extras.set()

@dp.message_handler(lambda msg: msg.text in ["Да", "Нет"], state=Order.choose_extras)
async def extras_decision(m: types.Message, state: FSMContext):
    if m.text == "Да":
        await m.answer("Выберите доп. услугу (можно несколько). Нажмите «✅ Готово» когда закончите.", reply_markup=extras_kb())
        await Order.extras_menu.set()
    else:
        await m.answer("Оставьте ваше имя:", reply_markup=types.ReplyKeyboardRemove())
        await Order.gather_name.set()

@dp.message_handler(lambda msg: msg.text == "✅ Готово", state=Order.extras_menu)
async def extras_done(m: types.Message, state: FSMContext):
    await m.answer("Оставьте ваше имя:", reply_markup=types.ReplyKeyboardRemove())
    await Order.gather_name.set()

@dp.message_handler(state=Order.extras_menu)
async def extras_choose(m: types.Message, state: FSMContext):
    text = m.text
    mapping = {
        "Окна 90k": "windows_90",
        "Окна 110k": "windows_110",
        "Стены": "walls",
        "Лестница": "staircase",
        "Стремянка": "ladder",
        "Стирка": "laundry",
        "Глажка": "ironing",
        "Балкон": "balcony",
        "2-й санузел": "second_wc",
        "Разложить вещи": "organize",
        "Лоток": "pet_litter",
        "Стул": "chair",
        "Кресло": "armchair",
        "Диван 2м": "sofa_2",
        "Диван 3м": "sofa_3",
        "Доп место": "sofa_extra",
        "Матрас 1сп": "mattress_1",
        "Матрас 2сп": "mattress_2",
        "Подушка": "pillow",
        "Одеяло/плед": "blanket",
        "Ковер": "carpet",
    }
    if text not in mapping:
        await m.answer("Пожалуйста, выберите услугу из списка или нажмите «✅ Готово».")
        return
    ekey = mapping[text]
    extra = EXTRAS[ekey]
    await state.update_data(current_extra_key=ekey)
    if extra["type"] == "fixed":
        # сразу добавляем
        data = await state.get_data()
        items = data.get("items", [])
        items.append({"name": extra["name"], "amount": extra["price"]})
        total = sum(i["amount"] for i in items)
        await state.update_data(items=items, total=total, current_extra_key=None)
        await m.answer(f"Добавлено: {extra['name']} — {fmt_money(extra['price'])} сум\nИтого: {fmt_money(total)} сум")
    elif extra["type"] in ("per_unit", "per_hour"):
        label = "количество" if extra["type"] == "per_unit" else "количество часов"
        await m.answer(f"Укажите {label} для «{extra['name']}» (числом):")
        await Order.extras_value.set()

@dp.message_handler(state=Order.extras_value)
async def extras_value(m: types.Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("Пожалуйста, отправьте число.")
        return
    qty = int(m.text)
    data = await state.get_data()
    ekey = data.get("current_extra_key")
    if not ekey:
        await m.answer("Не удалось определить услугу, попробуйте снова.")
        await Order.extras_menu.set()
        return
    extra = EXTRAS[ekey]
    amount = extra["price"] * qty
    name = f"{extra['name']} × {qty}"
    items = data.get("items", [])
    items.append({"name": name, "amount": amount})
    total = sum(i["amount"] for i in items)
    await state.update_data(items=items, total=total, current_extra_key=None)
    await m.answer(f"Добавлено: {name} — {fmt_money(amount)} сум\nИтого: {fmt_money(total)} сум")
    await Order.extras_menu.set()

# ===== Сбор контактов =====
@dp.message_handler(state=Order.gather_name)
async def get_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await m.answer("Оставьте номер телефона (например, +998XXXXXXXXX):")
    await Order.gather_phone.set()

@dp.message_handler(state=Order.gather_phone)
async def get_phone(m: types.Message, state: FSMContext):
    await state.update_data(phone=m.text.strip())
    await m.answer("Адрес (улица, дом, квартира):")
    await Order.gather_address.set()

@dp.message_handler(state=Order.gather_address)
async def get_address(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text.strip())
    await m.answer("Удобные дата и время (например, 25.08, 10:00):")
    await Order.gather_datetime.set()

@dp.message_handler(state=Order.gather_datetime)
async def get_datetime(m: types.Message, state: FSMContext):
    await state.update_data(when=m.text.strip())
    await m.answer("Комментарий/пожелания (можно пропустить, напишите «-»):")
    await Order.gather_comment.set()

@dp.message_handler(state=Order.gather_comment)
async def get_comment(m: types.Message, state: FSMContext):
    comment = m.text.strip()
    if comment == "-":
        comment = ""
    await state.update_data(comment=comment)
    data = await state.get_data()
    text = order_summary(data)
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    kb.add("✅ Подтвердить", "↩️ Изменить")
    await m.answer("Проверьте заказ:\n\n" + text, reply_markup=kb)
    await Order.confirm.set()

@dp.message_handler(lambda msg: msg.text == "↩️ Изменить", state=Order.confirm)
async def change_order(m: types.Message, state: FSMContext):
    await m.answer("Что изменить? Можно начать заново из меню.", reply_markup=main_menu_kb())
    await Order.choosing_category.set()

@dp.message_handler(lambda msg: msg.text == "✅ Подтвердить", state=Order.confirm)
async def confirm_order(m: types.Message, state: FSMContext):
    data = await state.get_data()
    text = "🆕 <b>Новый заказ</b>\n\n" + order_summary(data)
    # отправка админу
    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(ADMIN_CHAT_ID, text)
        except Exception:
            pass
    # подтверждение клиенту
    await m.answer("Спасибо! Заявка отправлена менеджеру.\nМы свяжемся с вами для подтверждения.", reply_markup=main_menu_kb())
    await state.finish()

# ===== Доп. услуги отдельно =====
@dp.message_handler(lambda msg: msg.text == "➕ Доп. услуги", state=Order.choosing_category)
async def only_extras(m: types.Message, state: FSMContext):
    await state.update_data(service_name="Доп. услуги", items=[], total=0)
    await m.answer("Выберите доп. услугу (можно несколько). Нажмите «✅ Готово» когда закончите.", reply_markup=extras_kb())
    await Order.extras_menu.set()

if __name__ == "__main__":
    print("Bot started (polling).")
    executor.start_polling(dp, skip_updates=True)
