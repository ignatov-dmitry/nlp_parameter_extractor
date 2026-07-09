from typing import Optional, List, Tuple
import json
import os

import pandas as pd
from fuzzywuzzy import fuzz


def remove_suffix(word: str) -> str:
    suffixes = ["чик", "ек", "ы", "и", "а", "я"]
    word_lower = word.lower()
    for suffix in suffixes:
        if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
            return word_lower[:-len(suffix)]
    return word_lower


class KnowledgeBase:
    def __init__(self) -> None:
        self.categories: dict[str, str] = {}
        self.parameters: dict[str, str] = {}
        self.values: dict[tuple[str, str, str], str] = {}
        self.synonyms: dict[str, str] = {}
        self.category_config: dict[str, dict] = {}
        
        # Проверяем наличие необходимых файлов
        self._check_required_files()
        
        # Загружаем синонимы и конфиг категорий
        self._load_synonyms()
        self._load_category_config()
    
    def _check_required_files(self) -> None:
        """Проверка наличия необходимых файлов"""
        required_files = [
            "data/db.xlsx",
            "data/synonyms.json",
            "data/category_config.json"
        ]
        missing_files = [f for f in required_files if not os.path.exists(f)]
        if missing_files:
            raise FileNotFoundError(f"Database or config files missing: {', '.join(missing_files)}")

    def _load_category_config(self) -> None:
        """Загрузка конфигурации категорий из JSON файла"""
        config_path = "data/category_config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self.category_config = json.load(f)
                    print(f"INFO: Загружена конфигурация категорий: {len(self.category_config)} категорий")
            except Exception as e:
                print(f"ERROR: Не удалось загрузить конфигурацию категорий: {e}")
                self.category_config = {}
        else:
            print(f"INFO: Файл конфигурации категорий не найден: {config_path}")
            self.category_config = {}

    def _load_synonyms(self) -> None:
        """Загрузка словаря синонимов из JSON файла"""
        synonyms_path = "data/synonyms.json"
        if os.path.exists(synonyms_path):
            try:
                with open(synonyms_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Конвертируем ключи в нижний регистр для регистронезависимого поиска
                    self.synonyms = {k.lower(): v for k, v in data.items()}
                    print(f"INFO: Загружено синонимов: {len(self.synonyms)}")
            except Exception as e:
                print(f"ERROR: Не удалось загрузить синонимы: {e}")
                self.synonyms = {}
        else:
            print(f"INFO: Файл синонимов не найден: {synonyms_path}")
            self.synonyms = {}

    def load_data(self, file_path: str = "data/db.xlsx") -> None:
        print("INFO: Загрузка базы знаний...")
        df = pd.read_excel(file_path)
        df.fillna("", inplace=True)

        for _, row in df.iterrows():
            category_name = str(row["category_name"]).strip().lower()
            category_id = str(row["category_id"]).strip()
            if not category_name or not category_id:
                continue
            self.categories[category_name] = category_id

            filter_name = str(row["filter_name"]).strip().lower()
            filter_id = str(row["filter_id"]).strip()
            if not filter_name or not filter_id:
                continue
            self.parameters[filter_name] = filter_id

            value = str(row["value"]).strip().lower()
            id_ = str(row["id"]).strip()
            if not value or not id_:
                continue
            self.values[(category_id, filter_id, value)] = id_

        del df
        print(f"INFO: Загружено параметров: {len(self.parameters)}, значений: {len(self.values)}")

    async def get_category_id(self, name: str) -> Optional[str]:
        return self.categories.get(name.lower())

    async def get_param_id(self, name: str) -> Optional[str]:
        return self.parameters.get(name.lower())

    async def get_value_id(self, param_id: str, value_name: str, category_id: str = None) -> Optional[str]:
        value_lower = value_name.strip().lower()
        
        if category_id:
            exact = self.values.get((str(category_id), str(param_id), value_lower))
            if exact:
                return exact
        
        exact_match = self.values.get((str(param_id), value_lower))
        if exact_match:
            return exact_match
        
        matches = []
        for (cat_id, filter_id, db_value), value_id in self.values.items():
            if str(filter_id) == str(param_id):
                if category_id and cat_id != str(category_id):
                    continue
                db_value_clean = db_value.strip().lower()
                if value_lower in db_value_clean or db_value_clean in value_lower:
                    matches.append((db_value_clean, value_id))
        
        if matches:
            matches.sort(key=lambda x: len(x[0]))
            return matches[0][1]
        
        root = value_lower[:4]
        for (cat_id, filter_id, db_value), value_id in self.values.items():
            if str(filter_id) == str(param_id):
                if category_id and cat_id != str(category_id):
                    continue
                db_value_lower = db_value.strip().lower()
                if db_value_lower.startswith(root):
                    return value_id
        
        value_stem = remove_suffix(value_lower)
        for (cat_id, filter_id, db_value), value_id in self.values.items():
            if str(filter_id) == str(param_id):
                if category_id and cat_id != str(category_id):
                    continue
                db_value_lower = db_value.strip().lower()
                db_stem = remove_suffix(db_value_lower)
                if value_stem and db_stem and (value_stem in db_stem or db_stem in value_stem):
                    return value_id
        
        value_stem = remove_suffix(value_lower)
        for (cat_id, filter_id, db_value), value_id in self.values.items():
            if str(filter_id) == str(param_id):
                if category_id and cat_id != str(category_id):
                    continue
                db_value_lower = db_value.strip().lower()
                db_stem = remove_suffix(db_value_lower)
                if value_stem and db_stem and (db_stem.startswith(value_stem) or value_stem.startswith(db_stem)):
                    return value_id
        
        return None

    async def get_filter_name_by_id(self, param_id: str) -> Optional[str]:
        for filter_name, filter_id in self.parameters.items():
            if filter_id == param_id:
                return filter_name
        return None

    async def get_allowed_params(self, category_id: str) -> list[str]:
        """
        Возвращает список имён разрешённых параметров для категории.
        Поддерживает как старый формат (список) так и новый (словарь с типами).
        """
        category_id_str = str(category_id)
        if category_id_str in self.category_config:
            allowed_params = self.category_config[category_id_str].get("allowed_params", [])
            # Новый формат - словарь {имя: тип}
            if isinstance(allowed_params, dict):
                params_list = list(allowed_params.keys())
            else:
                params_list = allowed_params
            print(f"CONFIG_ALLOWED_PARAMS: category {category_id_str} -> {len(params_list)} params")
            return params_list
        else:
            print(f"WARNING: No config found for category_id {category_id_str}, returning all params")
            return list(self.parameters.keys())

    async def get_param_type(self, category_id: str, param_name: str) -> str:
        """
        Возвращает тип параметра из конфига.
        Возможные значения: string, number, integer, boolean
        """
        category_id_str = str(category_id)
        if category_id_str in self.category_config:
            allowed_params = self.category_config[category_id_str].get("allowed_params", {})
            if isinstance(allowed_params, dict):
                return allowed_params.get(param_name.lower(), "string")
        return "string"

    async def find_value_matches(self, value_name: str, param_id: str, threshold: int = 70, max_results: int = 5, category_id: str = None) -> List[Tuple[str, str, int]]:
        """
        Поиск всех значений параметра с нечетким совпадением.
        Использует fuzz.partial_ratio для поиска частичных совпадений в значениях.
        
        Args:
            value_name: Название значения для поиска
            param_id: ID параметра (filter_id)
            threshold: Минимальный коэффициент схожести (0-100), по умолчанию 70
            max_results: Максимальное количество результатов
            
        Returns:
            Список кортежей (value_id, value_name, score) отсортированный по score в убывающем порядке
        """
        value_lower = value_name.strip().lower()
        matches = []
        
        # Проходим по ВСЕ значениям в базе
        for (cat_id, filter_id, db_value), value_id in self.values.items():
            if str(filter_id) == str(param_id):
                if category_id and cat_id != str(category_id):
                    continue
                db_value_lower = db_value.strip().lower()
                score = fuzz.partial_ratio(value_lower, db_value_lower)
                if "," in db_value_lower:
                    score = int(score * 0.5)
                if len(value_lower) <= 6 and len(db_value_lower) > len(value_lower) * 2:
                    score = int(score * 0.7)
                if score >= threshold:
                    matches.append((value_id, db_value, score))
        
        # Сортируем по score в убывающем порядке
        matches.sort(key=lambda x: x[2], reverse=True)
        
        # Возвращаем ID, название и score, ограничиваем количество результатов
        return [(m[0], m[1], m[2]) for m in matches[:max_results]]

    async def find_param_matches(self, name: str, category_id: Optional[str] = None, threshold: int = 70, max_results: int = 5) -> List[Tuple[str, int]]:
        """
        Поиск параметров с нечетким совпадением (fuzzy matching).
        Использует fuzz.partial_ratio для поиска частичных совпадений.
        Возвращает список кортежей (param_id, score) с score > threshold.
        
        Args:
            name: Название параметра для поиска
            category_id: ID категории (опционально)
            threshold: Минимальный коэффициент схожести (0-100), по умолчанию 70
            max_results: Максимальное количество результатов (3-5)
            
        Returns:
            Список кортежей (param_id, score) отсортированный по score в убывающем порядке
        """
        name_lower = name.lower()
        matches = []
        
        for param_name, param_id in self.parameters.items():
            score = fuzz.partial_ratio(name_lower, param_name.lower())
            if score >= threshold:
                matches.append((param_id, score, param_name))
        
        # Сортируем по score в убывающем порядке
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Возвращаем только ID и score, ограничиваем количество результатов
        return [(m[0], m[1]) for m in matches[:max_results]]

    async def find_param_by_fuzzy(self, name: str, category_id: Optional[str] = None) -> Optional[str]:
        """
        Поиск ID параметра по имени с поддержкой синонимов и конфигурации категорий.
        Сначала проверяет синонимы, затем использует конфигурацию для поиска типа.
        """
        name_lower = name.lower()
        
        # Проверка синонимов ПЕРЕД основным поиском
        if name_lower in self.synonyms:
            synonym_value = self.synonyms[name_lower]
            print(f"SYNONYM_FOUND: '{name}' -> '{synonym_value}'")
            # Ищем по значению синонима
            exact_match = self.parameters.get(synonym_value.lower())
            if exact_match:
                return exact_match
        
        # Специальная логика для "типа" с использованием конфигурации
        if name_lower in ["тип", "подтип", "вид товара"] and category_id is not None:
            category_id_str = str(category_id)
            if category_id_str in self.category_config:
                primary_type_filters = self.category_config[category_id_str].get("primary_type_filters", [])
                print(f"CONFIG_TYPE_FILTERS: category {category_id_str} -> {primary_type_filters}")
                
                for filter_name in primary_type_filters:
                    param_id = self.parameters.get(filter_name.lower())
                    if param_id:
                        print(f"TYPE_FILTER_MATCH: '{name}' -> '{filter_name}' (ID: {param_id})")
                        return param_id
            else:
                print(f"WARNING: No config found for category_id {category_id_str}")

        # Базовый exact match
        exact_match = self.parameters.get(name_lower)
        if exact_match:
            return exact_match
        
        name_lower = name.lower()
        
        if "глубин" in name_lower:
            for key in self.parameters:
                key_lower = key.lower()
                if "глубин" in key_lower:
                    return self.parameters[key]
        
        unit_suffix = None
        if category_id == "11":
            unit_suffix = ", см"
        elif category_id == "12":
            unit_suffix = ", мм"
        
        matching_keys = [key for key in self.parameters if key.startswith(name_lower)]
        
        if category_id == "11" and name_lower == "материал":
            matching_keys = [key for key in matching_keys if "арматуры" not in key and "плафона" not in key]
        
        if unit_suffix and matching_keys:
            for key in matching_keys:
                if unit_suffix in key:
                    return self.parameters[key]
        
        if matching_keys:
            return self.parameters[matching_keys[0]]
        
        return None
