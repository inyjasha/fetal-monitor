"""
Модуль для работы с медицинскими данными пациенток.
Загружает данные из Excel файлов и предоставляет интерфейс для доступа к ним.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Any
import os

class PatientDataManager:
    """Менеджер медицинских данных пациенток"""
    
    def __init__(self, data_root: str = "data"):
        self.data_root = Path(data_root)
        self.hypoxia_data = None
        self.regular_data = None
        self._load_data()
    
    def _load_data(self):
        """Загружает данные из Excel файлов"""
        try:
            hypoxia_path = self.data_root / "hypoxia.xlsx"
            regular_path = self.data_root / "regular.xlsx"
            
            if hypoxia_path.exists():
                self.hypoxia_data = pd.read_excel(hypoxia_path)
                # Нормализуем названия колонок
                self.hypoxia_data = self._normalize_columns(self.hypoxia_data)
                print(f"Загружено {len(self.hypoxia_data)} записей hypoxia")
            
            if regular_path.exists():
                self.regular_data = pd.read_excel(regular_path)
                self.regular_data = self._normalize_columns(self.regular_data)
                print(f"Загружено {len(self.regular_data)} записей regular")
                
        except Exception as e:
            print(f"Ошибка загрузки данных пациентов: {e}")
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Нормализует названия колонок для единообразия"""
        column_mapping = {
            'folder_id': 'folder_id',
            'Folder_id': 'folder_id',
            'Ph': 'Ph',
            'CO2': 'CO2', 
            'Glu': 'Glu',
            'LAC': 'LAC',
            'BE': 'BE',
            'Диагноз': 'diagnosis',
            'Газы крови': 'blood_gases'
        }
        
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        return df
    
    def _parse_folder_id(self, folder_id: Any) -> str:
        """Парсит folder_id, обрабатывая разные форматы"""
        if pd.isna(folder_id):
            return ""
        
        folder_str = str(folder_id).strip()
        # Обрабатываем случаи типа "155 156", "31,32"
        if ' ' in folder_str:
            return folder_str.split(' ')[0]
        elif ',' in folder_str:
            return folder_str.split(',')[0]
        else:
            return folder_str
    
    def get_patient_info(self, folder_id: str, group: str) -> Optional[Dict[str, Any]]:
        """
        Получает информацию о пациентке по folder_id и группе.
        Возвращает словарь с медицинскими данными.
        """
        folder_id_clean = self._parse_folder_id(folder_id)
        
        if group == "hypoxia" and self.hypoxia_data is not None:
            data_source = self.hypoxia_data
        elif group == "regular" and self.regular_data is not None:
            data_source = self.regular_data
        else:
            return self._get_default_patient_info()
        
        # Ищем запись по folder_id
        for _, row in data_source.iterrows():
            current_folder_id = self._parse_folder_id(row.get('folder_id', ''))
            if current_folder_id == folder_id_clean:
                return self._extract_patient_data(row)
        
        # Если не нашли, возвращаем данные по умолчанию
        return self._get_default_patient_info()
    
    def _extract_patient_data(self, row: pd.Series) -> Dict[str, Any]:
        """Извлекает медицинские данные из строки DataFrame"""
        patient_info = {
            # Основные демографические данные
            "age": self._extract_age_from_diagnosis(row.get('diagnosis', '')),
            "gestation_weeks": self._extract_gestation_weeks(row.get('diagnosis', '')),
            
            # Газы крови
            "Ph": self._parse_numeric_value(row.get('Ph')),
            "CO2": self._parse_numeric_value(row.get('CO2')),
            "Glu": self._parse_numeric_value(row.get('Glu')),
            "LAC": self._parse_numeric_value(row.get('LAC')),
            "BE": self._parse_numeric_value(row.get('BE')),
            
            # Диагноз и дополнительные данные
            "diagnosis": str(row.get('diagnosis', '')),
            "has_diabetes": 'ГСД' in str(row.get('diagnosis', '')),  # Гестационный сахарный диабет
            "has_anemia": 'анемия' in str(row.get('diagnosis', '')).lower(),
            "has_hypertension": 'преэклампсия' in str(row.get('diagnosis', '')).lower(),
            
            # Факторы риска
            "risk_factors": self._extract_risk_factors(str(row.get('diagnosis', '')))
        }
        
        return patient_info
    
    def _parse_numeric_value(self, value: Any) -> Optional[float]:
        """Парсит числовые значения, обрабатывая запятые как десятичные разделители"""
        if pd.isna(value) or value in ['-', '–', '']:
            return None
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                # Заменяем запятые на точки для русской нотации
                cleaned = value.replace(',', '.').replace(' ', '').strip()
                if cleaned in ['-', '–', '']:
                    return None
                return float(cleaned)
            else:
                return None
        except (ValueError, TypeError):
            return None
    
    def _extract_age_from_diagnosis(self, diagnosis: str) -> Optional[int]:
        """Извлекает возраст из текста диагноза"""
        import re
        if not diagnosis:
            return None
        
        # Ищем паттерны типа "в 33 года", "34 года", "в 35 лет"
        patterns = [
            r'в\s+(\d+)\s+год',  # "в 33 года"
            r'(\d+)\s+год',      # "33 года"  
            r'в\s+(\d+)\s+лет',  # "в 35 лет"
            r'(\d+)\s+лет'       # "35 лет"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, diagnosis)
            if match:
                try:
                    age = int(match.group(1))
                    # Проверяем разумные пределы возраста
                    if 15 <= age <= 50:
                        return age
                except (ValueError, IndexError):
                    continue
        
        return None
    
    def _extract_gestation_weeks(self, diagnosis: str) -> Optional[int]:
        """Извлекает срок беременности в неделях"""
        import re
        if not diagnosis:
            return None
        
        # Ищем паттерны типа "40-41 неделя", "37-38 недель"
        patterns = [
            r'(\d+)[-\s]+(\d+)\s+недел',  # "40-41 неделя"
            r'(\d+)\s+недел',             # "41 неделя"
            r'(\d+)[-\s]+(\d+)\s+нед',    # "40-41 нед"
            r'(\d+)\s+нед'                # "41 нед"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, diagnosis)
            if matches:
                try:
                    # Берем среднее значение для диапазона
                    if isinstance(matches[0], tuple):
                        weeks = (int(matches[0][0]) + int(matches[0][1])) / 2
                    else:
                        weeks = int(matches[0])
                    
                    if 20 <= weeks <= 42:  # Разумные пределы
                        return int(weeks)
                except (ValueError, IndexError):
                    continue
        
        return 40  # Значение по умолчанию для доношенной беременности
    
    def _extract_risk_factors(self, diagnosis: str) -> Dict[str, bool]:
        """Извлекает факторы риска из диагноза"""
        diagnosis_lower = diagnosis.lower()
        
        return {
            "diabetes": any(word in diagnosis_lower for word in ['гсд', 'сахарный диабет', 'диабет']),
            "anemia": any(word in diagnosis_lower for word in ['анемия', 'железодефицит']),
            "hypertension": any(word in diagnosis_lower for word in ['преэклампсия', 'гипертензия', 'повышенное давление']),
            "thyroid_issues": any(word in diagnosis_lower for word in ['гипотиреоз', 'тиреоидит', 'аит']),
            "kidney_issues": any(word in diagnosis_lower for word in ['пиелонефрит', 'цистит']),
            "thrombophilia": any(word in diagnosis_lower for word in ['тромбофилия', 'тромбоз']),
            "multiple_pregnancy": any(word in diagnosis_lower for word in ['двойня', 'тройня', 'многоплодная']),
            "previous_csection": any(word in diagnosis_lower for word in ['рубец на матке', 'кесарево']),
            "ivf": any(word in diagnosis_lower for word in ['эко', 'вспомогательные репродуктивные']),
            "infection": any(word in diagnosis_lower for word in ['инфекция', 'хламидиоз', 'герпес', 'впч'])
        }
    
    def _get_default_patient_info(self) -> Dict[str, Any]:
        """Возвращает данные по умолчанию, если информация о пациентке не найдена"""
        return {
            "age": 30,
            "gestation_weeks": 40,
            "Ph": 7.35,
            "CO2": 40.0,
            "Glu": 4.5,
            "LAC": 2.0,
            "BE": -2.0,
            "diagnosis": "Неизвестно",
            "has_diabetes": False,
            "has_anemia": False,
            "has_hypertension": False,
            "risk_factors": {
                "diabetes": False,
                "anemia": False,
                "hypertension": False,
                "thyroid_issues": False,
                "kidney_issues": False,
                "thrombophilia": False,
                "multiple_pregnancy": False,
                "previous_csection": False,
                "ivf": False,
                "infection": False
            }
        }

# Глобальный экземпляр менеджера
patient_manager = PatientDataManager()