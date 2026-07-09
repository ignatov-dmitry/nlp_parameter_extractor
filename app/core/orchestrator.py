import asyncio
from app.services.ai_service import AIService
from app.services.kb_service import KnowledgeBase


DIMENSION_PARAMS = ["высота", "ширина", "длина", "диаметр", "глубина", "радиус", "диапазон", "отступ", "вылет", "толщина"]


class Orchestrator:
    def __init__(self, ai_service: AIService, kb_service: KnowledgeBase) -> None:
        self.ai_service = ai_service
        self.kb_service = kb_service

    async def process_request(self, text: str) -> dict:
        valid_categories = list(self.kb_service.categories.keys())
        ai_data = await self.ai_service.extract_params(text, valid_categories=valid_categories)
        if not ai_data:
            return {"status": "error", "category_name": None, "category_id": None, "parameters": []}

        category_name = ai_data.get("category_name", "")
        category_id = await self.kb_service.get_category_id(category_name)
        price_min = ai_data.get("price_min")
        price_max = ai_data.get("price_max")

        valid_params = await self.kb_service.get_allowed_params(category_id) if category_id else []

        ai_data = await self.ai_service.extract_params(text, valid_params=valid_params, valid_categories=valid_categories)
        
        final_params = []
        type_params = []
        other_params = []
        for p in ai_data.get("parameters", []):
            param_name = p.get("name", "")
            param_value = p.get("value", [])
            if param_name.lower() in ["подтип", "категория", "вид товара"]:
                type_params.append(p)
            else:
                other_params.append(p)
        
        for p in type_params + other_params:
            param_name = p.get("name", "")
            param_value = p.get("value", [])
            param_id = await self.kb_service.find_param_by_fuzzy(param_name, category_id)
            real_filter_name = param_name
            
            if not param_id:
                final_params.append({
                    "name": param_name,
                    "id": None,
                    "value": param_value,
                    "value_id": None,
                    "filter_name": real_filter_name,
                })
                continue
            
            real_filter_name = await self.kb_service.get_filter_name_by_id(param_id)
            value_ids: list[str] = []
            value_names: list[str] = []
            
            for value in param_value:
                clean_value = value.strip().lower()
                
                # Проверка для числовых значений: используем строгое совпадение
                is_numeric = clean_value.isdigit()
                
                if is_numeric:
                    # Для чисел используем строгое совпадение (100% score)
                    value_id = await self.kb_service.get_value_id(param_id, clean_value, category_id=category_id)
                    if value_id and value_id not in value_ids:
                        value_ids.append(value_id)
                        value_names.append(clean_value)
                    continue
                
                # Ищем ВСЕ совпадения для значения с порогом 70%
                value_matches = await self.kb_service.find_value_matches(clean_value, param_id, threshold=70, max_results=5, category_id=category_id)
                
                if value_matches:
                    # Применяем умный порог: проверяем разницу в score
                    best_score = value_matches[0][2] if value_matches else 0
                    
                    # Проверяем разницу между лучшим и остальными результатами
                    should_return_single = True
                    if len(value_matches) > 1:
                        second_score = value_matches[1][2]
                        score_diff = best_score - second_score
                        if score_diff < 10:
                            should_return_single = False
                    
                    if should_return_single and best_score >= 95:
                        # Если лучший результат имеет score >= 95% и разница > 10%, берем только его
                        value_id, value_name, score = value_matches[0]
                        if value_id not in value_ids:
                            value_ids.append(value_id)
                            value_names.append(value_name)
                    else:
                        # Если score < 95% или разница < 10%, добавляем все найденные ID
                        for value_id, value_name, score in value_matches:
                            if value_id not in value_ids:
                                value_ids.append(value_id)
                                value_names.append(value_name)
                else:
                    # Если не найдено через fuzzy matching, пробуем обычный поиск
                    value_id = await self.kb_service.get_value_id(param_id, clean_value, category_id=category_id)
                    if not value_id and param_name.lower() in ["подтип", "категория", "вид товара"]:
                        for fallback_param in ["подкатегория", "категория мебели"]:
                            fallback_param_id = await self.kb_service.find_param_by_fuzzy(fallback_param, category_id)
                            if fallback_param_id:
                                # Ищем все совпадения для fallback параметра с порогом 70%
                                fallback_matches = await self.kb_service.find_value_matches(clean_value, fallback_param_id, threshold=70, max_results=5, category_id=category_id)
                                
                                if fallback_matches:
                                    # Применяем умный порог для fallback результатов
                                    best_fallback_score = fallback_matches[0][2] if fallback_matches else 0
                                    
                                    # Проверяем разницу между лучшим и остальными результатами
                                    should_return_single_fallback = True
                                    if len(fallback_matches) > 1:
                                        second_fallback_score = fallback_matches[1][2]
                                        score_diff_fallback = best_fallback_score - second_fallback_score
                                        if score_diff_fallback < 10:
                                            should_return_single_fallback = False
                                    
                                    if should_return_single_fallback and best_fallback_score >= 95:
                                        # Если лучший результат имеет score >= 95% и разница > 10%, берем только его
                                        fallback_id, fallback_name, score = fallback_matches[0]
                                        if fallback_id not in value_ids:
                                            value_ids.append(fallback_id)
                                            value_names.append(fallback_name)
                                    else:
                                        # Если score < 95% или разница < 10%, добавляем все найденные ID
                                        for fallback_id, fallback_name, score in fallback_matches:
                                            if fallback_id not in value_ids:
                                                value_ids.append(fallback_id)
                                                value_names.append(fallback_name)
                                    
                                    real_filter_name = await self.kb_service.get_filter_name_by_id(fallback_param_id)
                                    break
                    
                    if value_id and value_id not in value_ids:
                        value_ids.append(value_id)

            final_params.append({
                "name": param_name,
                "id": param_id,
                "value": param_value,
                "value_id": value_ids if value_ids else None,
                "value_names": value_names if value_names else None,
                "filter_name": real_filter_name,
            })
        
        # Фильтруем параметры: добавляем только те, которые имеют значения или явно извлечены из текста
        filtered_params = []
        for param in final_params:
            # Добавляем параметр если:
            # 1. У него есть найденные value_id (явно извлечен и найден в базе)
            # 2. Или если param_value не пусто (явно извлечен AI, даже если не найден в базе)
            if param["value_id"] is not None or (param["value"] and len(param["value"]) > 0):
                filtered_params.append(param)
        
        final_params = filtered_params

        price_str = f"{price_min}-{price_max}" if price_min or price_max else "не указана"
        lines = [
            f"КАТЕГОРИЯ: {category_name} (ID: {category_id})",
            f"ЦЕНА: {price_str}",
            "ПАРАМЕТРЫ:",
        ]
        for param in final_params:
            values_str = ", ".join(param["value"]) if isinstance(param["value"], list) else str(param["value"])
            if not values_str or values_str.strip() == "":
                values_str = "[значение не распознано]"
            display_name = param.get("filter_name", param["name"])
            param_id_str = param.get("id", "N/A")
            
            if param["id"] is None:
                lines.append(f"- {display_name} [ID: {param_id_str}]: {values_str} -> (Этого параметра нет в Excel)")
            elif param["value_id"] is None:
                lines.append(f"- {display_name} [ID: {param_id_str}]: {values_str} -> (Значения нет в базе)")
            else:
                # Используем value_names если доступны, иначе value_id
                if param.get("value_names"):
                    names_with_ids = []
                    for name, vid in zip(param["value_names"], param["value_id"]):
                        names_with_ids.append(f"{name} [ID: {vid}]")
                    output_str = ", ".join(names_with_ids)
                else:
                    value_id_str = ", ".join(param["value_id"]) if isinstance(param["value_id"], list) else str(param["value_id"])
                    output_str = f"[ID: {value_id_str}]"
                lines.append(f"- {display_name} [ID: {param_id_str}]: {output_str}")

        debug_info = "\n".join(lines)

        return {
            "status": "success",
            "category_name": category_name,
            "category_id": category_id,
            "parameters": final_params,
            "price_min": price_min,
            "price_max": price_max,
            "debug_info": debug_info,
        }
