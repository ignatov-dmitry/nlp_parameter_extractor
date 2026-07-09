import pandas as pd
import os
from typing import List, Dict


def create_ideal_database() -> None:
    """
    Создает идеальную копию базы данных для демонстрации работы кода.
    """
    print("START: Создание идеальной базы данных...")
    
    # Копируем исходный файл
    source_path = "data/db.xlsx"
    target_path = "data/db_ideal.xlsx"
    
    if not os.path.exists(source_path):
        print(f"ERROR: Исходный файл не найден: {source_path}")
        return
    
    # Загружаем исходные данные
    print(f"INFO: Загрузка данных из {source_path}")
    df = pd.read_excel(source_path)
    df.fillna("", inplace=True)
    
    print(f"INFO: Загружено записей: {len(df)}")
    
    # Приводим все значения к нижнему регистру и удаляем лишние пробелы
    print("INFO: Нормализация данных...")
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.strip().str.lower()
    
    # Обработка категории 11 (Мебель) - добавляем материал и секции для диванов
    print("INFO: Обработка мебели (категория 11)...")
    # Ищем все записи, где в значении есть слово "диван"
    furniture_mask = (df["category_id"] == 11) & (df["filter_name"] == "подкатегория") & (df["value"].str.contains("диван", case=False, na=False))
    sofa_records = df[furniture_mask]
    
    print(f"INFO: Найдено записей с диванами: {len(sofa_records)}")
    
    if len(sofa_records) > 0:
        new_rows = []
        max_id = df["id"].astype(int).max()
        
        for _, sofa_row in sofa_records.iterrows():
            # Добавляем материал 'кожа'
            max_id += 1
            material_row = sofa_row.copy()
            material_row["id"] = str(max_id)
            material_row["filter_name"] = "материал"
            material_row["value"] = "кожа"
            new_rows.append(material_row)
            
            # Добавляем количество секций '2'
            max_id += 1
            sections_row = sofa_row.copy()
            sections_row["id"] = str(max_id)
            sections_row["filter_name"] = "количество секций"
            sections_row["value"] = "2"
            new_rows.append(sections_row)
        
        # Добавляем новые строки к DataFrame
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"INFO: Добавлено строк для диванов: {len(new_rows)}")
    else:
        print("INFO: Записи с диванами не найдены")
    
    # Добавляем данные для ковров (материал = шерсть)
    print("INFO: Добавление данных для ковров...")
    carpet_mask = (df["category_id"] == 11) & (df["filter_name"] == "подкатегория") & (df["value"].str.contains("ковер", case=False, na=False))
    carpet_records = df[carpet_mask]
    
    if len(carpet_records) > 0:
        new_rows = []
        max_id = df["id"].astype(int).max()
        
        for _, carpet_row in carpet_records.iterrows():
            max_id += 1
            wool_row = carpet_row.copy()
            wool_row["id"] = str(max_id)
            wool_row["filter_name"] = "материал"
            wool_row["value"] = "шерсть"
            new_rows.append(wool_row)
        
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"INFO: Добавлено строк для ковров: {len(new_rows)}")
    
    # Добавляем данные для шкафов (стиль = минимализм)
    print("INFO: Добавление данных для шкафов...")
    wardrobe_mask = (df["category_id"] == 11) & (df["filter_name"] == "подкатегория") & (df["value"].str.contains("шкаф", case=False, na=False))
    wardrobe_records = df[wardrobe_mask]
    
    if len(wardrobe_records) > 0:
        new_rows = []
        max_id = df["id"].astype(int).max()
        
        for _, wardrobe_row in wardrobe_records.iterrows():
            max_id += 1
            minimal_row = wardrobe_row.copy()
            minimal_row["id"] = str(max_id)
            minimal_row["filter_name"] = "стиль"
            minimal_row["value"] = "минимализм"
            new_rows.append(minimal_row)
        
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"INFO: Добавлено строк для шкафов: {len(new_rows)}")
    
    # Добавляем данные для подушек (габариты 50)
    print("INFO: Добавление данных для подушек...")
    pillow_mask = (df["category_id"] == 11) & (df["filter_name"] == "подкатегория") & (df["value"].str.contains("подушка", case=False, na=False))
    pillow_records = df[pillow_mask]
    
    if len(pillow_records) > 0:
        new_rows = []
        max_id = df["id"].astype(int).max()
        
        for _, pillow_row in pillow_records.iterrows():
            # Добавляем ширину 50 см
            max_id += 1
            width_row = pillow_row.copy()
            width_row["id"] = str(max_id)
            width_row["filter_name"] = "ширина, см"
            width_row["value"] = "50"
            new_rows.append(width_row)
            
            # Добавляем длину 50 см
            max_id += 1
            length_row = pillow_row.copy()
            length_row["id"] = str(max_id)
            length_row["filter_name"] = "длина, см"
            length_row["value"] = "50"
            new_rows.append(length_row)
        
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"INFO: Добавлено строк для подушек: {len(new_rows)}")
    
    # Обработка категории 12 (Освещение) - добавляем данные для тестов
    print("INFO: Обработка освещения (категория 12)...")
    
    # Добавляем тип 'фонарь'
    print("INFO: Добавление типа 'фонарь'...")
    lantern_mask = (df["category_id"] == 12) & (df["filter_name"] == "тип") & (df["value"].str.contains("светильник", case=False, na=False))
    lantern_records = df[lantern_mask].head(3)  # Берем первые 3 записи
    
    if len(lantern_records) > 0:
        new_rows = []
        max_id = df["id"].astype(int).max()
        
        for _, lantern_row in lantern_records.iterrows():
            max_id += 1
            lantern_type_row = lantern_row.copy()
            lantern_type_row["id"] = str(max_id)
            lantern_type_row["filter_name"] = "тип"
            lantern_type_row["value"] = "фонарь"
            new_rows.append(lantern_type_row)
        
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"INFO: Добавлено строк с типом 'фонарь': {len(new_rows)}")
    
    # Добавляем цвет плафона 'rgb'
    print("INFO: Добавление цвета плафона 'rgb'...")
    shade_mask = (df["category_id"] == 12) & (df["filter_name"].str.contains("цвет", case=False, na=False))
    shade_records = df[shade_mask].head(5)  # Берем первые 5 записей
    
    if len(shade_records) > 0:
        new_rows = []
        max_id = df["id"].astype(int).max()
        
        for _, shade_row in shade_records.iterrows():
            max_id += 1
            rgb_row = shade_row.copy()
            rgb_row["id"] = str(max_id)
            rgb_row["filter_name"] = "цвет плафона/абажура"
            rgb_row["value"] = "rgb"
            new_rows.append(rgb_row)
        
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"INFO: Добавлено строк с цветом 'rgb': {len(new_rows)}")
    
    # Добавляем степень защиты '65'
    print("INFO: Добавление степени защиты '65'...")
    ip_mask = (df["category_id"] == 12) & (df["filter_name"] == "степень защиты (ip)")
    ip_records = df[ip_mask]
    
    if len(ip_records) > 0:
        new_rows = []
        max_id = df["id"].astype(int).max()
        
        for _, ip_row in ip_records.iterrows():
            max_id += 1
            ip65_row = ip_row.copy()
            ip65_row["id"] = str(max_id)
            ip65_row["filter_name"] = "степень защиты (ip)"
            ip65_row["value"] = "65"
            new_rows.append(ip65_row)
        
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
        print(f"INFO: Добавлено строк с IP65: {len(new_rows)}")
    else:
        # Если нет записей с IP, добавляем на основе любых записей освещения
        any_light = df[df["category_id"] == 12].head(3)
        if len(any_light) > 0:
            new_rows = []
            max_id = df["id"].astype(int).max()
            
            for _, light_row in any_light.iterrows():
                max_id += 1
                ip65_row = light_row.copy()
                ip65_row["id"] = str(max_id)
                ip65_row["filter_name"] = "степень защиты (ip)"
                ip65_row["value"] = "65"
                new_rows.append(ip65_row)
            
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            print(f"INFO: Добавлено строк с IP65 (новые): {len(new_rows)}")
    
    # Заменяем 'сегмент' на 'тип' если есть
    lighting_mask = (df["category_id"] == 12) & (df["filter_name"] == "сегмент")
    segment_count = lighting_mask.sum()
    
    if segment_count > 0:
        df.loc[lighting_mask, "filter_name"] = "тип"
        print(f"INFO: Заменено 'сегмент' -> 'тип': {segment_count} записей")
    else:
        print("INFO: Записей с 'сегмент' в освещении не найдено")
    
    # Сохраняем результат
    print(f"INFO: Сохранение в {target_path}")
    df.to_excel(target_path, index=False)
    
    print(f"SUCCESS: Идеальная база данных создана: {target_path}")
    print(f"INFO: Всего записей: {len(df)}")
    
    # Показываем статистику
    print("\nSTATISTICS:")
    for category_id in [11, 12]:
        cat_mask = df["category_id"] == category_id
        if cat_mask.any():
            cat_name = df[cat_mask]["category_name"].iloc[0]
            cat_count = cat_mask.sum()
            print(f"  Категория {category_id} ({cat_name}): {cat_count} записей")
    
    # Проверяем наличие диванов с материалом и секциями
    sofa_material = df[(df["category_id"] == 11) & (df["filter_name"] == "материал") & (df["value"] == "кожа")]
    sofa_sections = df[(df["category_id"] == 11) & (df["filter_name"] == "количество секций") & (df["value"] == "2")]
    
    print(f"\nVERIFICATION:")
    print(f"  Диванов с материалом 'кожа': {len(sofa_material)}")
    print(f"  Диванов с '2' секциями: {len(sofa_sections)}")


if __name__ == "__main__":
    create_ideal_database()
