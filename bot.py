import openai, re, logging, conf, os, json
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from transformers import GPT2TokenizerFast

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

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

prompt = ""
prompt_tokens = []

async def get_user_data(user_id):
    try:
        with open(f"user_data/{user_id}.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

async def save_user_data(user_id, user_data):
    with open(f"user_data/{user_id}.json", "w") as f:
        json.dump(user_data, f)
        

# Обработка команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот на основе ChatGPT.")
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    if user_data is None:
        await save_user_data(user_id, {
        'model_engine' : "text-davinci-003",
        'temperature' : 0.3,
        'max_tokens' : 2047,
        'top_p' : 0.2,
        'frequency_penalty' : 0.2,
        'presence_penalty' : 0.2,
        'prompt' : "",
        'base' : ""
    })

# Обработка команды /context
@dp.message_handler(commands=['context'])
async def show_context(message: types.Message):
    if prompt:
        await message.answer(prompt + "\nprompt_tokens = " + str(len(prompt_tokens)))
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
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    user_input = message.text

    # получить список токенов из ввода
    input_tokens = tokenizer.tokenize(user_input)
    prompt_tokens = tokenizer.tokenize(user_data['prompt'])
    # вычислить общее количество токенов
    total_tokens = len(input_tokens) + len(prompt_tokens)

    # вычислить количество лишних токенов
    excess_tokens = max(0, total_tokens - (4097 - user_data['max_tokens']))

    # добавить ввод к истории, удаляя необходимое количество токенов
    if excess_tokens > 0:
        prompt_tokens = prompt_tokens[excess_tokens:]
        user_data['prompt'] = tokenizer.convert_tokens_to_string(prompt_tokens) + " " + user_input
    else:
        user_data['prompt'] += user_input

    # Генерация ответа на основе текста сообщения
    try:
        response = openai.Completion.create(
        engine=user_data['engine'],
        prompt=user_data['prompt'],
        max_tokens=user_data['max_tokens']
        )

        # Получение ответа из сгенерированного текста
        answer = response.choices[0].text.strip()

        # получить список токенов из ответа
        response_tokens = tokenizer.tokenize(answer)
        prompt_tokens = tokenizer.tokenize(user_data['prompt'])

        # вычислить общее количество токенов
        total_tokens = len(response_tokens) + len(prompt_tokens)

        # вычислить количество лишних токенов
        excess_tokens = max(0, total_tokens - user_data['max_tokens'])

        # добавить ответ к истории, удаляя необходимое количество токенов
        if excess_tokens > 0:
            prompt_tokens = prompt_tokens[excess_tokens:]
            user_data['prompt'] = tokenizer.convert_tokens_to_string(prompt_tokens) + " " + answer
        else:
            user_data['prompt'] += answer
        # Отправка ответа пользователю
        await message.answer(answer)
        await save_user_data(user_id,user_data)
    except openai.error.RateLimitError as e:
        await message.answer('Превышен лимит запросов:',e)



if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
