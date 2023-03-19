import openai, re, logging, os, json, tiktoken
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
# from transformers import GPT2TokenizerFast

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

encoding = tiktoken.get_encoding("cl100k_base")

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
    await message.answer("Привет! Я бот на основе ChatGPT. Вы можете изменить параметры генерации с помощью команд.")
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    if user_data is None:
        await save_user_data(user_id, {
        'engine' : "gpt-3.5-turbo",
        'temperature' : 0.3,
        'max_tokens' : 2047,
        'top_p' : 0.2,
        'frequency_penalty' : 0.2,
        'presence_penalty' : 0.2,
        'messages' = [{"role": "system", "content": "You are a helpful assistant."}]
    })

# Обработка команды /context
@dp.message_handler(commands=['context'])
async def show_context(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    if user_data['messages']:
        await message.answer(user_data['messages'])
    else:
        await message.answer( "Контекст пуст.")


# Обработка команды /clear
@dp.message_handler(commands=['clear'])
async def clear_context(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    user_data['messages'] = []
    await message.answer("Контекст очищен.")
    await save_user_data(user_id, user_data)


# Обработка команды /t
@dp.message_handler(commands=['t'])
async def set_temperature(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    try:
        temp = float(message.get_args())
        # Проверяем, что значение находится в допустимых пределах
        if 0.0 <= temp <= 2.0:
            # Устанавливаем новое значение
            user_data['temperature'] = temp
            await message.answer(f"Temperature установлена в {temp}")
            await save_user_data(user_id, user_data) 
        else:
            await message.answer("Неверное значение. Используйте значения между 0.0 и 2.0. Большие значения делают ответы более случайными.")
    except IndexError:
        await message.answer("Введите значение между 0.0 и 2.0. Большие значения делают ответы более случайными.")
    
@dp.message_handler(commands=['max'])
async def set_max_tokens(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    try:
        max_tokens = int(message.get_args())
        # Проверяем, что значение находится в допустимых пределах
        if 0 <= max_tokens <= 4000:
            # Устанавливаем новое значение
            user_data['max_tokens'] = max_tokens
            await message.answer(f"Установлено значение max_tokens = {max_tokens}")
            await save_user_data(user_id, user_data) 
        else:
            await message.answer("Неверное значение. Используйте значения до 4000.")
    except IndexError:
        await message.answer("Введите значение до 4000.")


def num_tokens(messages):
  """Returns the number of tokens used by a list of messages."""
  num_tokens = 0
  for message in messages:
    num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
    for key, value in message.items():
      num_tokens += len(encoding.encode(value))
      if key == "name":  # if there's a name, the role is omitted
        num_tokens += -1  # role is always required and always 1 token
      num_tokens += 2  # every reply is primed with <im_start>assistant
   return num_tokens

# Добавить новое сообщение к списку, удаляя лишние при превышении длины.
def update_messages(messages, message):
  pass
  

        
# Обработка всех остальных сообщений
@dp.message_handler()
async def any_message(message: types.Message):
    # Получение текста сообщения от пользователя
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    
    user_message = {"role": "user", "content":message.text}
    
    user_data['messages'] = update_messages(user_data['messages'], user_message)
    
    # вычислить общее количество токенов
    total_tokens = num_tokens(user_data['messages'])

    # вычислить количество лишних токенов
    excess_tokens = max(0, total_tokens - (4097 - user_data['max_tokens']))

    # Удалить лишнее
    if excess_tokens > 0:
        prompt_tokens = prompt_tokens[excess_tokens:]
        user_data['prompt'] = tokenizer.convert_tokens_to_string(prompt_tokens) + " " + user_input
    else:
        user_data['prompt'] += user_input

    # Генерация ответа на основе текста сообщения
    try:
        response = openai.Completion.create(
        engine=user_data['engine'],
        prompt=user_data['base'] + user_data['prompt'],
        temperature = user_data['temperature'],
        #frequency_penalty = user_data['frequency_penalty'],
        #presence_penalty = user_data['presence_penalty'],
        max_tokens=user_data['max_tokens']
        )

        # Получение ответа из сгенерированного текста
        answer = response.choices[0].text.strip()
        await message.answer(answer)
        
        # получить список токенов из ответа
        response_tokens = tokenizer.tokenize(answer)
        prompt_tokens = tokenizer.tokenize(user_data['prompt'])

        # вычислить общее количество токенов
        total_tokens = len(response_tokens) + len(prompt_tokens) + len(base_tokens)

        # вычислить количество лишних токенов
        excess_tokens = max(0, total_tokens - user_data['max_tokens'])

        # добавить ответ к истории, удаляя необходимое количество токенов
        if excess_tokens > 0:
            prompt_tokens = prompt_tokens[excess_tokens:]
            user_data['prompt'] = tokenizer.convert_tokens_to_string(prompt_tokens) + " " + answer
        else:
            user_data['prompt'] += answer
        
        await save_user_data(user_id,user_data)
    except openai.error.RateLimitError as e:
        await message.answer('Превышен лимит запросов:' + str(e))



if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
