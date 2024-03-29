import openai, re, logging, os, json, tiktoken, aiofiles
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, executor, types
from datetime import datetime

load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')
bot = Bot(token=str(os.getenv('TELEGRAM_TOKEN')), parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot)
encoding = tiktoken.get_encoding("cl100k_base")

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)

async def get_user_data(user_id):
    try:
        async with aiofiles.open(f"user_data/{user_id}.json") as f:
            return json.loads(await f.read())
    except Exception as e:
        print(str(e))
        if await save_user_data(user_id, DEFAULT_USER_DATA):
            return await get_user_data(user_id)
        else:
            return DEFAULT_USER_DATA

async def save_user_data(user_id, user_data):
    try:
        async with aiofiles.open(f"user_data/{user_id}.json", "w") as f:
            await f.write(json.dumps(user_data))
        return True
    except Exception as e:
        print(str(e))
        return False


DEFAULT_USER_DATA = {
        'engine' : "gpt-3.5-turbo",
        'temperature' : 0.6,
        'max_tokens' : 2047,
        'top_p' : 0.2,
        'frequency_penalty' : 0.2,
        'presence_penalty' : 0.2,
        'messages' : [{"role": "system", "content": "You are a helpful assistant. Always use <code> html tag to format program code! Do not use it in other text! Solve tasks step by step."}]
    }


# Обработка команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот на основе ChatGPT. Вы можете изменить параметры генерации с помощью команд.")
    user_id = message.from_user.id
    await save_user_data(user_id, DEFAULT_USER_DATA)
    

# Обработка команды /context
@dp.message_handler(commands=['context'])
async def show_context(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    try:
        await message.answer(user_data['messages'])
    except Exception as e:
        await message.answer(str(e))
    

# Обработка команды /clear
@dp.message_handler(commands=['clear'])
async def clear_context(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    user_data['messages'] = user_data['messages'][:0]
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
            await message.answer("Неверное значение. Используйте значения до 4000. Обратите внимание, что суммарный размер запроса и ответа не должен превышать 4097 токенов.")
    except IndexError:
        await message.answer("Введите значение до 4000.")



@dp.message_handler(commands=['system'])
async def set_max_tokens(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    user_data['messages'][0] = {"role": "system", "content":message.get_args()}
    

@dp.message_handler(commands=['answer'])
async def answer_gpt3(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    try:
        response = openai.Completion.create(
        engine='text-davinci-003',
        prompt=message.text,
        temperature = user_data['temperature'],
        max_tokens=user_data['max_tokens']
        )

        answer = response.choices[0].text.strip()
        await message.answer(answer)
        
    except Exception as e:
        await message.answer(str(e))
    
@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    await message.answer("Доступны следующие команды:\n\
    /t 0-2.0 - изменить параметр temperature;\n\
    /max 1-4097 - изменить параметр max_tokens;\n\
    /system текст - изменить системное сообщение;\n\
    /clear - очистить историю чата;\n\
    /context - показать историю чата;\n\
    /answer текст - обратиться к модели gpt-3;\n\
    /start - установить значения параметров по-умолчанию."
    )
    

def num_tokens(messages):
    """Returns the number of tokens used by a list of messages."""
    num_tokens = 0
    for message_dict in messages:
        num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
        for key, value in message_dict.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant   
    return num_tokens

# Обновить messages
def update_messages(user_data, user_message_dict):
    user_data['messages'].append(user_message_dict)
    while num_tokens(user_data['messages']) > (4090-user_data['max_tokens']):
        del user_data['messages'][1]
    return user_data
        
# Обработка всех остальных сообщений
@dp.message_handler()
async def any_message(message: types.Message):
    # Получение текста сообщения от пользователя
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    print(message.text)
    user_message_dict = {"role": "user", "content":message.text}
    
    user_data = update_messages(user_data, user_message_dict)

    # Запись времени вызова функции any_message
    start_time = datetime.now()

    # Генерация ответа на основе текста сообщения
    try:
        response = openai.ChatCompletion.create(
          model="gpt-3.5-turbo",
          messages=user_data['messages'],
          temperature = user_data['temperature'],
          max_tokens = user_data['max_tokens']
          )

        # Получение ответа из сгенерированного текста
        answer = '{content} \nFinish reason = {finish_reason};\nUsage = {usage};\nResponse time = {time_taken} s.'.format(
            content=response['choices'][0]['message']['content'], 
            finish_reason=response['choices'][0]['finish_reason'], 
            usage = response['usage'], 
            time_taken = (datetime.now() - start_time).seconds) # Вычисление времени выполнения функции в секундах
        print(answer)
        try:
            await message.answer(answer)
        except Exception as e:
            await message.answer(str(e))         
            
            
        user_data['messages'].append(response['choices'][0]['message'])
        
        await save_user_data(user_id,user_data)
    except openai.error.RateLimitError as e:
        await message.answer('Превышен лимит запросов:' + str(e))
    except Exception as e:
        await message.answer(str(e))



if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp, skip_updates=True)
