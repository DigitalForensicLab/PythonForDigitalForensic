# DIRECTORY = r"D:\27908-КТ\OCR_1"  # Змініть на ваш шлях!

#!/usr/bin/env python3
"""
Скрипт для перевірки можливості відкриття графічних файлів
"""

import os
from pathlib import Path
from PIL import Image
import sys
import shutil
from typing import List, Tuple


def format_size(size_bytes: int) -> str:
    """
    Форматує розмір файлу в читабельний вигляд
    
    Args:
        size_bytes: розмір в байтах
        
    Returns:
        str: форматований розмір (напр. "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def check_image(file_path: str) -> Tuple[bool, str, int]:
    """
    Перевіряє чи можна відкрити графічний файл
    
    Args:
        file_path: шлях до файлу
        
    Returns:
        tuple: (успішність, повідомлення про помилку або успіх, розмір файлу в байтах)
    """
    # Отримуємо розмір файлу
    try:
        file_size = os.path.getsize(file_path)
    except:
        file_size = 0
    
    try:
        with Image.open(file_path) as img:
            # Перевіряємо чи файл дійсно можна завантажити
            img.verify()
        
        # Повторно відкриваємо для отримання інформації (після verify() потрібно)
        with Image.open(file_path) as img:
            format_name = img.format
            size = img.size
            mode = img.mode
            
        return True, f"OK - {format_name}, {size[0]}x{size[1]}, {mode}", file_size
        
    except FileNotFoundError:
        return False, "Файл не знайдено", file_size
    except PermissionError:
        return False, "Немає доступу до файлу", file_size
    except Image.UnidentifiedImageError:
        return False, "Не розпізнано як зображення", file_size
    except Exception as e:
        return False, f"Помилка: {type(e).__name__} - {str(e)}", file_size


def check_images_in_directory(directory: str, extensions: List[str] = None) -> dict:
    """
    Перевіряє всі файли у директорії на можливість відкриття як зображення
    
    Args:
        directory: шлях до директорії
        extensions: не використовується (для зворотної сумісності)
        
    Returns:
        dict: статистика перевірки
    """
    results = {
        'valid': [],
        'invalid': [],
        'total': 0,
        'total_files': 0,
        'total_size': 0,
        'valid_size': 0
    }
    
    print(f"Сканування директорії: {directory}")
    print("Перевіряються ВСІ файли (без фільтрації за розширенням)")
    print("-" * 80)
    
    # Рекурсивний пошук файлів
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            results['total_files'] += 1
            
            # Перевіряємо всі файли без винятків
            results['total'] += 1
            is_valid, message, file_size = check_image(file_path)
            
            results['total_size'] += file_size
            
            if is_valid:
                results['valid'].append((file_path, message, file_size))
                results['valid_size'] += file_size
                print(f"✓ {file_path}")
                print(f"  {message}")
                print(f"  Розмір: {format_size(file_size)}")
            else:
                results['invalid'].append((file_path, message, file_size))
                print(f"✗ {file_path}")
                print(f"  {message}")
                print(f"  Розмір: {format_size(file_size)}")
            print()
    
    return results


def check_images_from_list(file_list_path: str) -> dict:
    """
    Перевіряє файли зі списку (один файл на рядок)
    
    Args:
        file_list_path: шлях до текстового файлу зі списком файлів
        
    Returns:
        dict: статистика перевірки
    """
    results = {
        'valid': [],
        'invalid': [],
        'total': 0,
        'total_files': 0,
        'total_size': 0,
        'valid_size': 0
    }
    
    try:
        with open(file_list_path, 'r', encoding='utf-8') as f:
            files = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"Помилка читання списку файлів: {e}")
        return results
    
    results['total_files'] = len(files)
    
    print(f"Перевірка {len(files)} файлів зі списку")
    print("-" * 80)
    
    for file_path in files:
        if not os.path.exists(file_path):
            results['invalid'].append((file_path, "Файл не існує", 0))
            print(f"✗ {file_path}")
            print(f"  Файл не існує")
            print()
            continue
            
        results['total'] += 1
        is_valid, message, file_size = check_image(file_path)
        
        results['total_size'] += file_size
        
        if is_valid:
            results['valid'].append((file_path, message, file_size))
            results['valid_size'] += file_size
            print(f"✓ {file_path}")
            print(f"  {message}")
            print(f"  Розмір: {format_size(file_size)}")
        else:
            results['invalid'].append((file_path, message, file_size))
            print(f"✗ {file_path}")
            print(f"  {message}")
            print(f"  Розмір: {format_size(file_size)}")
        print()
    
    return results


def save_results(results: dict, output_dir: str = "."):
    """
    Зберігає результати у файли
    
    Args:
        results: словник з результатами
        output_dir: директорія для збереження результатів
    """
    # Зберігаємо валідні файли
    valid_file = os.path.join(output_dir, "valid_images.txt")
    with open(valid_file, 'w', encoding='utf-8') as f:
        for file_path, message, file_size in results['valid']:
            f.write(f"{file_path}\n")
    
    # Зберігаємо невалідні файли з причинами
    invalid_file = os.path.join(output_dir, "invalid_images.txt")
    with open(invalid_file, 'w', encoding='utf-8') as f:
        for file_path, message, file_size in results['invalid']:
            f.write(f"{file_path} | {message}\n")
    
    # Зберігаємо звіт
    report_file = os.path.join(output_dir, "check_report.txt")
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("ЗВІТ ПРО ПЕРЕВІРКУ ГРАФІЧНИХ ФАЙЛІВ\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Всього файлів у директорії: {results['total_files']}\n")
        f.write(f"Всього перевірено файлів: {results['total']}\n")
        f.write(f"Валідних файлів: {len(results['valid'])} ({len(results['valid'])/results['total']*100:.1f}%)\n")
        f.write(f"Невалідних файлів: {len(results['invalid'])} ({len(results['invalid'])/results['total']*100:.1f}%)\n\n")
        
        f.write(f"Загальний обсяг всіх файлів: {format_size(results['total_size'])}\n")
        f.write(f"Загальний обсяг валідних файлів: {format_size(results['valid_size'])} ({results['valid_size']/results['total_size']*100:.1f}%)\n")
        f.write(f"Загальний обсяг невалідних файлів: {format_size(results['total_size'] - results['valid_size'])} ({(results['total_size'] - results['valid_size'])/results['total_size']*100:.1f}%)\n\n")
        
        if results['invalid']:
            f.write("Типи помилок:\n")
            error_types = {}
            for _, message, _ in results['invalid']:
                error_type = message.split('-')[0].strip() if '-' in message else message
                error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                f.write(f"  {error_type}: {count}\n")
    
    print(f"\nРезультати збережено:")
    print(f"  Валідні файли: {valid_file}")
    print(f"  Невалідні файли: {invalid_file}")
    print(f"  Звіт: {report_file}")


def print_summary(results: dict):
    """
    Виводить підсумкову статистику
    """
    print("\n" + "=" * 80)
    print("ПІДСУМОК")
    print("=" * 80)
    print(f"Всього файлів у директорії: {results['total_files']}")
    print(f"Всього перевірено файлів: {results['total']}")
    print(f"Валідних файлів: {len(results['valid'])} ({len(results['valid'])/results['total']*100:.1f}%)")
    print(f"Невалідних файлів: {len(results['invalid'])} ({len(results['invalid'])/results['total']*100:.1f}%)")
    print()
    print(f"Загальний обсяг всіх файлів: {format_size(results['total_size'])}")
    print(f"Загальний обсяг валідних файлів: {format_size(results['valid_size'])} ({results['valid_size']/results['total_size']*100:.1f}%)")
    print(f"Загальний обсяг невалідних файлів: {format_size(results['total_size'] - results['valid_size'])} ({(results['total_size'] - results['valid_size'])/results['total_size']*100:.1f}%)")
    
    if results['invalid']:
        print("\nНайпоширеніші помилки:")
        error_types = {}
        for _, message, _ in results['invalid']:
            error_type = message.split('-')[0].strip() if '-' in message else message
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {error_type}: {count}")


def copy_valid_files(results: dict, source_dir: str, output_dir: str):
    """
    Копіює всі валідні файли в окрему директорію зі збереженням структури
    
    Args:
        results: словник з результатами
        source_dir: вихідна директорія
        output_dir: директорія для копіювання валідних файлів
    """
    if not results['valid']:
        print("\nНемає валідних файлів для копіювання.")
        return
    
    # Створюємо директорію для валідних файлів
    valid_dir = os.path.join(output_dir, "valid_files")
    
    print(f"\n{'=' * 80}")
    print(f"КОПІЮВАННЯ ВАЛІДНИХ ФАЙЛІВ")
    print(f"{'=' * 80}")
    print(f"Копіюється {len(results['valid'])} файлів...")
    print(f"Директорія призначення: {valid_dir}\n")
    
    copied_count = 0
    failed_count = 0
    copied_size = 0
    
    for file_path, message, file_size in results['valid']:
        try:
            # Визначаємо відносний шлях від вихідної директорії
            rel_path = os.path.relpath(file_path, source_dir)
            dest_path = os.path.join(valid_dir, rel_path)
            
            # Створюємо необхідні піддиректорії
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Копіюємо файл
            shutil.copy2(file_path, dest_path)
            copied_count += 1
            copied_size += file_size
            
            if copied_count % 100 == 0:
                print(f"Скопійовано {copied_count}/{len(results['valid'])} файлів...")
                
        except Exception as e:
            failed_count += 1
            print(f"✗ Помилка копіювання {file_path}: {e}")
    
    print(f"\n{'=' * 80}")
    print(f"РЕЗУЛЬТАТ КОПІЮВАННЯ")
    print(f"{'=' * 80}")
    print(f"Успішно скопійовано: {copied_count} файлів")
    print(f"Помилок копіювання: {failed_count}")
    print(f"Загальний обсяг скопійованих файлів: {format_size(copied_size)}")
    print(f"Директорія з валідними файлами: {valid_dir}")
    
    return valid_dir


def main():
    """
    Основна функція
    """
    # ============================================================
    # НАЛАШТУВАННЯ: Вкажіть шлях до вашої директорії тут
    # ============================================================
    # DIRECTORY = r"D:\27908-КТ\OCR_1"  # Змініть на ваш шлях!
    # DIRECTORY = r"D:\27908-КТ\OCR_1"  # Змініть на ваш шлях!
    DIRECTORY = r"D:\19024-RN-NEW-01\OCR"
    DIRECTORY = r"D:\27908-КТ\OCR_2" # 
       
    
    
    
    
    # Опціонально: вкажіть шлях до файлу зі списком файлів
    # FILE_LIST = "/path/to/file_list.txt"
    FILE_LIST = None
    
    # Копіювати валідні файли в окрему директорію?
    COPY_VALID_FILES = True  # True - копіювати, False - не копіювати
    
    # Визначаємо директорію для збереження результатів - там де знаходиться скрипт
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    OUTPUT_DIR = SCRIPT_DIR
    # ============================================================
    
    # Перевірка чи встановлено Pillow
    try:
        import PIL
        print(f"Використовується Pillow версії: {PIL.__version__}\n")
    except ImportError:
        print("Помилка: Потрібно встановити Pillow")
        print("Виконайте: pip install Pillow --break-system-packages")
        sys.exit(1)
    
    print(f"Результати будуть збережені в: {OUTPUT_DIR}\n")
    
    # Визначаємо режим роботи
    source_directory = None
    if FILE_LIST is not None:
        # Перевірка зі списку
        if not os.path.isfile(FILE_LIST):
            print(f"Помилка: {FILE_LIST} не знайдено")
            sys.exit(1)
        print(f"Режим: Перевірка файлів зі списку")
        print(f"Список файлів: {FILE_LIST}\n")
        results = check_images_from_list(FILE_LIST)
    else:
        # Перевірка директорії
        if not os.path.isdir(DIRECTORY):
            print(f"Помилка: {DIRECTORY} не є директорією або не існує")
            print(f"\nБудь ласка, відредагуйте змінну DIRECTORY у коді та вкажіть правильний шлях.")
            sys.exit(1)
        print(f"Режим: Перевірка всіх файлів у директорії")
        print(f"Директорія: {DIRECTORY}\n")
        source_directory = DIRECTORY
        results = check_images_in_directory(DIRECTORY)
    
    # Виводимо підсумок та зберігаємо результати
    if results['total'] > 0:
        print_summary(results)
        save_results(results, OUTPUT_DIR)
        
        # Копіюємо валідні файли якщо увімкнено
        if COPY_VALID_FILES and source_directory:
            copy_valid_files(results, source_directory, OUTPUT_DIR)
    else:
        print("\nНе знайдено жодного файлу для перевірки.")


if __name__ == "__main__":
    main()