#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для дослідження SQLite баз даних
Дата: 2025-11-07

"""

import sqlite3
import hashlib
import os
import json
import csv
from datetime import datetime
from pathlib import Path
import sys

class SQLiteForensics:
    def __init__(self, directory_path, output_dir=None):
        """
        Ініціалізація класу для дослідження SQLite файлів
        
        Args:
            directory_path: Шлях до каталогу з файлами
            output_dir: Каталог для збереження звіту (за замовчуванням - поточна папка зі скриптом)
        """
        self.directory_path = Path(directory_path)
        
        # Якщо output_dir не вказано, використовуємо папку зі скриптом
        if output_dir is None:
            script_dir = Path(__file__).parent.resolve()
            self.output_dir = script_dir / "forensic_report"
        else:
            self.output_dir = Path(output_dir)
            
        self.output_dir.mkdir(exist_ok=True)
        self.report = []
        
    def calculate_hash(self, filepath, hash_type='sha256'):
        """Обчислення хеш-суми файлу"""
        hash_func = hashlib.new(hash_type)
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            return f"Помилка: {str(e)}"
    
    def get_file_metadata(self, filepath):
        """Отримання метаданих файлу"""
        stat = filepath.stat()
        return {
            'filename': filepath.name,
            'full_path': str(filepath),
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024*1024), 2),
            'created': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'accessed': datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S'),
            'md5': self.calculate_hash(filepath, 'md5'),
            'sha1': self.calculate_hash(filepath, 'sha1'),
            'sha256': self.calculate_hash(filepath, 'sha256')
        }
    
    def check_database_integrity(self, db_path):
        """Перевірка цілісності бази даних"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            result = cursor.fetchone()[0]
            conn.close()
            return result
        except Exception as e:
            return f"Помилка: {str(e)}"
    
    def get_database_info(self, db_path):
        """Отримання інформації про структуру бази даних"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Версія SQLite
            cursor.execute("SELECT sqlite_version();")
            sqlite_version = cursor.fetchone()[0]
            
            # Список таблиць
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Інформація про кожну таблицю
            tables_info = {}
            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM '{table}';")
                    row_count = cursor.fetchone()[0]
                    
                    cursor.execute(f"PRAGMA table_info('{table}');")
                    columns = cursor.fetchall()
                    
                    tables_info[table] = {
                        'row_count': row_count,
                        'columns': [{'id': col[0], 'name': col[1], 'type': col[2], 
                                   'not_null': col[3], 'default': col[4], 'pk': col[5]} 
                                  for col in columns]
                    }
                except Exception as e:
                    tables_info[table] = {'error': str(e)}
            
            # Індекси
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
            indexes = [row[0] for row in cursor.fetchall()]
            
            # Тригери
            cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger';")
            triggers = [row[0] for row in cursor.fetchall()]
            
            conn.close()
            
            return {
                'sqlite_version': sqlite_version,
                'tables_count': len(tables),
                'tables': tables,
                'tables_info': tables_info,
                'indexes': indexes,
                'triggers': triggers
            }
        except Exception as e:
            return {'error': str(e)}
    
    def export_table_data(self, db_path, table_name, output_path):
        """Експорт даних таблиці в CSV"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"SELECT * FROM '{table_name}';")
            rows = cursor.fetchall()
            
            # Отримання назв колонок
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Запис у CSV
            csv_path = output_path / f"{db_path.stem}_{table_name}.csv"
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                writer.writerows(rows)
            
            conn.close()
            return str(csv_path)
        except Exception as e:
            return f"Помилка експорту: {str(e)}"
    
    def search_deleted_records(self, db_path):
        """Пошук можливих видалених записів через freelist"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Перевірка наявності freelist
            cursor.execute("PRAGMA freelist_count;")
            freelist_count = cursor.fetchone()[0]
            
            conn.close()
            return {
                'freelist_pages': freelist_count,
                'note': 'Для глибокого аналізу використовуйте спеціалізовані інструменти'
            }
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_database(self, db_path):
        """Повний аналіз однієї бази даних"""
        print(f"\n{'='*60}")
        print(f"Аналіз: {db_path.name}")
        print(f"{'='*60}")
        
        db_report = {}
        
        # Метадані файлу
        print("- Збір метаданих файлу...")
        db_report['metadata'] = self.get_file_metadata(db_path)
        
        # Перевірка цілісності
        print("- Перевірка цілісності бази даних...")
        db_report['integrity'] = self.check_database_integrity(db_path)
        
        # Інформація про структуру
        print("- Аналіз структури бази даних...")
        db_report['database_info'] = self.get_database_info(db_path)
        
        # Пошук видалених записів
        print("- Пошук видалених записів...")
        db_report['deleted_records'] = self.search_deleted_records(db_path)
        
        # Експорт даних таблиць
        if 'tables' in db_report['database_info']:
            print("- Експорт даних таблиць...")
            export_dir = self.output_dir / 'exported_data'
            export_dir.mkdir(exist_ok=True)
            
            db_report['exported_tables'] = {}
            for table in db_report['database_info']['tables']:
                csv_path = self.export_table_data(db_path, table, export_dir)
                db_report['exported_tables'][table] = csv_path
                print(f"  Експортовано: {table}")
        
        return db_report
    
    def find_sqlitedb_files(self):
        """Пошук всіх .sqlitedb файлів у каталозі"""
        patterns = ['*.sqlitedb', '*.sqlite', '*.db', '*.sqlite3']
        files = []
        for pattern in patterns:
            files.extend(self.directory_path.rglob(pattern))
        return files
    
    def generate_report(self):
        """Генерація звіту про всі знайдені бази даних"""
        print(f"\n{'#'*60}")
        print("СУДОВО-ЕКСПЕРТНЕ ДОСЛІДЖЕННЯ SQLite БАЗ ДАНИХ")
        print(f"{'#'*60}")
        print(f"Дата дослідження: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Каталог дослідження: {self.directory_path}")
        print(f"Папка для звітів: {self.output_dir.resolve()}")
        
        # Пошук файлів
        db_files = self.find_sqlitedb_files()
        print(f"\nЗнайдено файлів баз даних: {len(db_files)}")
        
        if not db_files:
            print("Файли SQLite не знайдені!")
            return
        
        # Аналіз кожного файлу
        full_report = {
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'directory': str(self.directory_path),
            'output_directory': str(self.output_dir.resolve()),
            'total_files': len(db_files),
            'databases': {}
        }
        
        for db_file in db_files:
            try:
                db_report = self.analyze_database(db_file)
                full_report['databases'][str(db_file)] = db_report
            except Exception as e:
                print(f"Помилка при аналізі {db_file.name}: {str(e)}")
                full_report['databases'][str(db_file)] = {'error': str(e)}
        
        # Збереження звіту в JSON
        report_path = self.output_dir / f"forensic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(full_report, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"Звіт збережено: {report_path.resolve()}")
        print(f"Експортовані дані: {(self.output_dir / 'exported_data').resolve()}")
        print(f"{'='*60}")
        
        # Генерація текстового звіту
        self.generate_text_report(full_report)
        
        return full_report
    
    def generate_text_report(self, data):
        """Генерація текстового звіту для судового висновку"""
        report_path = self.output_dir / f"text_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("ВИСНОВОК ЕКСПЕРТА\n")
            f.write("Комп'ютерно-технічна експертиза SQLite баз даних\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Дата дослідження: {data['analysis_date']}\n")
            f.write(f"Досліджуваний каталог: {data['directory']}\n")
            f.write(f"Папка зі звітами: {data['output_directory']}\n")
            f.write(f"Кількість виявлених файлів: {data['total_files']}\n\n")
            
            for db_path, db_info in data['databases'].items():
                f.write("\n" + "-"*80 + "\n")
                f.write(f"ФАЙЛ: {Path(db_path).name}\n")
                f.write("-"*80 + "\n\n")
                
                if 'error' in db_info:
                    f.write(f"ПОМИЛКА: {db_info['error']}\n")
                    continue
                
                # Метадані
                f.write("1. МЕТАДАНІ ФАЙЛУ\n")
                f.write(f"   Повний шлях: {db_info['metadata']['full_path']}\n")
                f.write(f"   Розмір: {db_info['metadata']['size_mb']} MB ({db_info['metadata']['size_bytes']} байт)\n")
                f.write(f"   Дата створення: {db_info['metadata']['created']}\n")
                f.write(f"   Дата модифікації: {db_info['metadata']['modified']}\n")
                f.write(f"   MD5: {db_info['metadata']['md5']}\n")
                f.write(f"   SHA-1: {db_info['metadata']['sha1']}\n")
                f.write(f"   SHA-256: {db_info['metadata']['sha256']}\n\n")
                
                # Цілісність
                f.write("2. ПЕРЕВІРКА ЦІЛІСНОСТІ\n")
                f.write(f"   Результат: {db_info['integrity']}\n\n")
                
                # Структура бази
                if 'database_info' in db_info and 'error' not in db_info['database_info']:
                    f.write("3. СТРУКТУРА БАЗИ ДАНИХ\n")
                    f.write(f"   Версія SQLite: {db_info['database_info']['sqlite_version']}\n")
                    f.write(f"   Кількість таблиць: {db_info['database_info']['tables_count']}\n\n")
                    
                    f.write("   Таблиці:\n")
                    for table, info in db_info['database_info']['tables_info'].items():
                        if 'error' not in info:
                            f.write(f"   - {table}: {info['row_count']} записів, {len(info['columns'])} колонок\n")
                    
                    f.write(f"\n   Індекси: {', '.join(db_info['database_info']['indexes']) if db_info['database_info']['indexes'] else 'Відсутні'}\n")
                    f.write(f"   Тригери: {', '.join(db_info['database_info']['triggers']) if db_info['database_info']['triggers'] else 'Відсутні'}\n\n")
                
                # Видалені записи
                if 'deleted_records' in db_info:
                    f.write("4. АНАЛІЗ ВИДАЛЕНИХ ЗАПИСІВ\n")
                    if 'freelist_pages' in db_info['deleted_records']:
                        f.write(f"   Freelist сторінок: {db_info['deleted_records']['freelist_pages']}\n")
                        f.write(f"   Примітка: {db_info['deleted_records']['note']}\n\n")
        
        print(f"Текстовий звіт збережено: {report_path.resolve()}")


def main():
    """Головна функція"""
    print("\n" + "="*60)
    print("ПРОГРАМА СУДОВО-ЕКСПЕРТНОГО ДОСЛІДЖЕННЯ SQLite")
    print("="*60 + "\n")
    
    # ========================================================================
    # ВКАЖІТЬ ТУТ ШЛЯХ ДО КАТАЛОГУ З SQLite ФАЙЛАМИ
    # ========================================================================
    # Приклади:
    # DIRECTORY_PATH = "C:/Users/Expert/Documents/evidence"
    # DIRECTORY_PATH = "/home/expert/case_files"
    # DIRECTORY_PATH = "D:/Експертизи/2025/Справа_123"
    
    DIRECTORY_PATH = r"D:\27908-КТ\RESULT\DATABASES"  # <-- ВКАЖІТЬ ШЛЯХ ТУТ
    
    # ========================================================================
    
    # Якщо шлях не вказано в коді, використовуємо аргументи командного рядка або запитуємо
    if not DIRECTORY_PATH:
        if len(sys.argv) > 1:
            directory = sys.argv[1]
        else:
            directory = input("Введіть шлях до каталогу з файлами SQLite: ").strip()
    else:
        directory = DIRECTORY_PATH
        print(f"Використовується шлях з коду: {directory}")
    
    if not os.path.exists(directory):
        print(f"ПОМИЛКА: Каталог '{directory}' не знайдено!")
        return
    
    # Визначення поточної папки скрипту
    script_location = Path(__file__).parent.resolve()
    print(f"Поточна папка скрипту: {script_location}")
    print(f"Результати будуть збережені в: {script_location / 'forensic_report'}\n")
    
    # Створення об'єкту дослідження (output_dir=None означає використання папки скрипту)
    forensics = SQLiteForensics(directory, output_dir=None)
    
    # Генерація звіту
    forensics.generate_report()
    
    print("\nДослідження завершено!")


if __name__ == "__main__":
    main()
