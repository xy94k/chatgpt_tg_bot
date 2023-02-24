import openai, re, logging, conf, os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

# Объект бота
"""
proxy_url = 'http://proxy.server:3128'
bot = Bot(token=str(os.getenv('TELEGRAM_TOKEN')), proxy=proxy_url)
"""
bot = Bot(token=str(os.getenv('TELEGRAM_TOKEN')))

# Диспетчер для бота
dp = Dispatcher(bot)
# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

prompt = ""

# Обработка команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот на основе ChatGPT.")

# Обработка команды /context
@dp.message_handler(commands=['context'])
async def show_context(message: types.Message):
    if prompt:
        await message.answer(prompt)
    else:
        await message.answer( "Контекст пуст.")


# Обработка команды /clear
@dp.message_handler(commands=['clear'])
async def clear_context(message: types.Message):
    global prompt
    prompt = ""
    await message.answer("Контекст очищен.")

"""
# Обработка команды /t
@dp.message_handler(commands=['t'])
async def set_temperature(message: types.Message):
    try:
        temp = float(message.get_args())
        # Проверяем, что значение находится в допустимых пределах
        if 0.0 <= temp <= 2.0:
            # Устанавливаем новое значение
            prompt["temperature"] = temp
            await message.answer(f"Temperature is set to {temp}")
        else:
            await message.answer("Invalid temperature value. Please use a value between 0.0 and 2.0")
    except IndexError:
        await message.answer("Please provide a temperature value")
"""


# Обработка всех остальных сообщений
@dp.message_handler()
async def any_message(message: types.Message):
    # Получение текста сообщения от пользователя
    global prompt
    user_input = message.text

    # получить список токенов из ввода
    input_tokens = re.findall(r'\w+|[^\w\s]',user_input)
    prompt_tokens = re.findall(r'\w+|[^\w\s]',prompt)
    # вычислить общее количество токенов
    total_tokens = len(input_tokens) + len(prompt_tokens)

    # вычислить количество лишних токенов
    excess_tokens = max(0, total_tokens - conf.max_prompt_tokens)

    # вычислить количество лишних символов
    excess_chars = 0
    for i in range(excess_tokens):
        excess_chars += len(prompt_tokens[i])
    # добавить ввод к истории, удаляя необходимое количество символов
    if excess_tokens > 0:
        prompt = prompt[excess_chars:] + user_input
    else:
        prompt += user_input

    # Генерация ответа на основе текста сообщения
    try:
        response = openai.Completion.create(
        engine=conf.model_engine,
        prompt=prompt,
        max_tokens=conf.max_tokens
        )

        # Получение ответа из сгенерированного текста
        answer = response.choices[0].text.strip()

        # получить список токенов из ответа
        response_tokens = re.findall(r'\w+|[^\w\s]',answer)
        prompt_tokens = re.findall(r'\w+|[^\w\s]',prompt)

        # вычислить общее количество токенов
        total_tokens = len(response_tokens) + len(prompt_tokens)

        # вычислить количество лишних токенов
        excess_tokens = max(0, total_tokens - conf.max_prompt_tokens)

        # вычислить количество лишних символов
        excess_chars = 0
        for i in range(excess_tokens):
            excess_chars += len(prompt_tokens[i])

        # добавить ответ к истории, удаляя необходимое количество токенов
        if excess_tokens > 0:
            prompt = prompt[excess_chars:] + answer
        else:
            prompt += answer)
        # Отправка ответа пользователю
        await message.answer(answer))
    except openai.error.RateLimitError as e:
        await message.answer('Превышен лимит запросов:',e)



if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
