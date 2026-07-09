import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import AsyncOpenAI


class AIService:
    EXTRACTION_SCHEMA: dict[str, Any] = {
        "type": "function",
        "function": {
            "name": "extract_entities",
            "description": "Извлекает категорию товара, его характеристики и диапазон цен из текста",
            "parameters": {
                "type": "object",
                "properties": {
                    "category_name": {
                        "type": "string",
                        "description": "Обобщенная категория товара, например: Освещение, Мебель"
                    },
                    "parameters": {
                        "type": "array",
                        "description": "Список найденных характеристик, включая тип изделия",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Название характеристики, например: Тип, Бренд, Цвет арматуры"
                                },
                                "value": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Значения характеристики, например: [кровать] или [Эра, Розовый]"
                                }
                            },
                            "required": ["name", "value"]
                        }
                    },
                    "price_min": {
                        "type": "integer",
                        "description": "Минимальная цена. Переводи разговорные числа в цифры, например 'восемь двести' -> 8200"
                    },
                    "price_max": {
                        "type": "integer",
                        "description": "Максимальная цена"
                    }
                },
                "required": ["category_name", "parameters"]
            }
        }
    }

    def __init__(self) -> None:
        load_dotenv()
        self.client = AsyncOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url="https://api.proxyapi.ru/openai/v1"
        )

    async def call_llm(self, system_prompt: str, user_message: str) -> str:
        """
        Отправляет запрос в LLM и возвращает текстовый ответ.
        Реализует умный retry с экспоненциальной задержкой.
        
        Аргументы:
            system_prompt: Системный промпт для LLM
            user_message: Сообщение пользователя
        
        Возвращает:
            Текстовый ответ от LLM
        """
        import asyncio
        
        max_retries = 3
        retry_delay = 2.0
        
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.0
                )
                
                llm_response = response.choices[0].message.content
                print(f"RAW_LLM_RESPONSE: {llm_response}")
                return llm_response
                
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "rate limit" in error_str.lower()
                is_server_error = "503" in error_str or "service unavailable" in error_str.lower()
                
                if (is_rate_limit or is_server_error) and attempt < max_retries - 1:
                    print(f"LLM_RETRY: attempt {attempt + 1}/{max_retries}, waiting {retry_delay}s before retry, error='{error_str}'")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2.0
                else:
                    print(f"LLM_CALL_ERROR: {error_str}")
                    raise

    def build_extraction_schema(self, valid_params: dict) -> dict:
        """
        Динамически строит JSON Schema для function calling на основе
        словаря параметров {имя: тип} из category_config.json.
        """
        type_map = {
            "string": {"type": "string"},
            "number": {"type": "number"},
            "integer": {"type": "integer"},
            "boolean": {"type": "boolean"},
        }
        properties = {
            "category_name": {
                "type": "string",
                "description": "Обобщенная категория товара, например: Освещение, Мебель"
            },
            "price_min": {
                "type": "integer",
                "description": "Минимальная цена. Переводи разговорные числа в цифры, например 'восемь двести' -> 8200"
            },
            "price_max": {
                "type": "integer",
                "description": "Максимальная цена"
            }
        }
        for param_name, param_type in valid_params.items():
            field_schema = type_map.get(param_type, {"type": "string"}).copy()
            if param_type == "boolean":
                field_schema["description"] = f"True если пользователь упомянул '{param_name}', иначе null"
            elif param_type in ("number", "integer"):
                field_schema["description"] = f"Числовое значение для '{param_name}'. Конвертируй единицы измерения согласно правилам."
            else:
                field_schema["description"] = f"Значение параметра '{param_name}'"
            safe_key = param_name.replace(" ", "_").replace(",", "").replace("/", "_").replace("(", "").replace(")", "").replace(".", "")
            properties[safe_key] = field_schema
        return {
            "type": "function",
            "function": {
                "name": "extract_entities",
                "description": "Извлекает категорию товара, его характеристики и диапазон цен из текста",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": ["category_name"]
                }
            }
        }

    async def extract_params(self, text: str, valid_params: list[str] = None, valid_categories: list[str] = None) -> dict:
        """
        Извлекает сущности (категорию и параметры) из входящего текста.

        Args:
            text: Входящий текст для анализа
            valid_params: Список доступных названий параметров
            valid_categories: Список доступных названий категорий

        Returns:
            Словарь с извлеченными сущностями
        """
        try:
            system_prompt = (
                "Ты - универсальный AI-помощник для извлечения характеристик товаров. "
                "Ты получаешь на вход текст пользователя и динамический список ДОСТУПНЫХ ПАРАМЕТРОВ для текущей категории. "
                "Твоя задача - извлечь характеристики и сопоставить их СТРОГО с именами параметров из переданного списка. "
                "ПРАВИЛО ФАКТОВ (КРИТИЧЕСКИ ВАЖНО): Извлекай ТОЛЬКО те свойства и параметры, которые ЯВНО написаны в тексте пользователя. "
                "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО додумывать материал, цвет, стиль или другие свойства на основе типа товара "
                "(например, не добавляй 'металл' для светильников или 'дерево' для столов, если об этом не написано прямо в тексте). "
                "ПРАВИЛО ИМЕНОВАНИЯ КЛЮЧЕЙ: Ключи параметров в твоем ответе должны СТРОГО совпадать с названиями категорий "
                "(названиями колонок) из переданного тебе списка. Если предмет в списке доступных параметров числится под "
                "категорию 'Тип' или 'Категория мебели', ты обязан использовать именно эти ключи. "
                "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО использовать дефолтное слово 'тип', если такого названия нет в списке параметров "
                "для извлеченного значения. "
                "ПРАВИЛО КОНКРЕТНОСТИ: Всегда извлекай КОНКРЕТНЫЙ тип товара (например, 'бра', 'торшер', 'угловой диван', "
                "'настольная лампа') в параметр 'тип' или 'вид товара'. НИКОГДА не заменяй конкретное название товара на общую "
                "категорию (например, не заменяй 'бра' на 'освещение', не заменяй 'угловой диван' на 'мебель'). "
                "Сохраняй специфичность и точность названия. "
                "Для мебели параметр цвета называется 'цвет' - используй именно это имя. Никогда не используй 'цвет производителя' для мебели.  "
                "СТРОГАЯ АТОМАРНОСТЬ: Запрещено объединять характеристики с типом товара. "
                "Извлекай только базовое название изделия (например, 'диван', 'кровать', 'бра') в поле 'тип'. "
                "Все уточнения (например, 'двухсекционный', 'модульный', 'угловой', 'раскладной') выноси только в "
                "соответствующие технические параметры и НИКОГДА не добавляй их в значение параметра 'тип'. "
                "Если не уверен в названии типа, используй самое простое существительное. "
                "СТРОГИЙ ФИЛЬТР ПАРАМЕТРОВ: КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО извлекать параметры, если их названия отсутствуют в списке "
                "ДОСТУПНЫХ ПАРАМЕТРОВ. Игнорируй любые характеристики в тексте пользователя, которые не соответствуют именам "
                "из переданного списка. ЗАПРЕЩЕНО галлюцинировать или выдумывать названия параметров - используй ТОЛЬКО те, что "
                "есть в списке. "
                "ПРАВИЛО БАЗОВЫХ ВЕЛИЧИН: Ты обязан применять абсолютные и строгие правила конвертации. "
                "1. Для МЕБЕЛИ (ID 11): все габариты конвертируй СТРОГО умножением метров на 100 (2 метра -> 200, 1.5 метра -> 150). "
                "2. Для ОСВЕЩЕНИЯ (ID 12): все габариты конвертируй СТРОГО умножением метров на 1000 (2 метра -> 2000, 1.5 метра -> 1500). Сантиметры умножай на 10 (20 см -> 200, 50 см -> 500). "
                "Никогда не отклоняйся от этих правил. Всегда выводи только число без единиц измерения."
                "ПРАВИЛО ИЕРАРХИИ: Даже если пользователь в тексте указал только узкий вид товара, ты обязан проанализировать "
                "список доступных параметров и логически найти его родительскую категорию (например, 'Диваны и кресла'), "
                "если она присутствует в списке. Выводи ОБА значения: и узкий тип, и широкую группу, используя для них точные "
                "совпадения из списка. "
                "ПРАВИЛО ОБЩЕНИЯ: Если в тексте есть несколько значений одной характеристики (например, 'Эра, Розанный'), "
                "включи их все в массив. Если в тексте есть диапазон (например, 'от 100 до 200'), включи оба числа. "
                "Если в тексте есть разговорные числа (например, 'пять тыщ'), переведи их в цифры (5000)."
            )
            if valid_categories:
                system_prompt += f" ДОСТУПНЫЕ КАТЕГОРИИ: {', '.join(valid_categories)}. Ты ОБЯЗАН выбрать категорию СТРОГО из этого списка. Если товар (например, шнур, датчик) не подходит идеально, отнеси его к ближайшей по смыслу из доступных (например, к Освещению)."
            if valid_params:
                system_prompt += f" ДОСТУПНЫЕ ПАРАМЕТРЫ: {', '.join(valid_params)}. В поле name для parameters используй ТОЛЬКО точные совпадения из этого списка."
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                tools=[self.EXTRACTION_SCHEMA],
                tool_choice={"type": "function", "function": {"name": "extract_entities"}},
                temperature=0.0
            )
            
            tool_call = response.choices[0].message.tool_calls[0]
            return json.loads(tool_call.function.arguments)
            
        except Exception as e:
            return {}
