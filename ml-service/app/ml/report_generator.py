# app/ml/report_generator.py
"""
Модуль для генерации PDF отчетов по сессиям с поддержкой русского языка.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

class PDFReportGenerator:
    """Генератор PDF отчетов для сессий мониторинга плода"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.fonts_registered = False
        self._register_fonts()
    
    def _register_fonts(self):
        """Регистрирует шрифты с поддержкой кириллицы"""
        try:
            # Список возможных путей к шрифтам (в порядке приоритета)
            font_paths = [
                # 1. Локальная папка fonts в проекте
                ("DejaVuSans", "fonts/DejaVuSans.ttf"),
                ("DejaVuSans-Bold", "fonts/DejaVuSans-Bold.ttf"),
                
                # 2. Абсолютные пути к DejaVu
                ("DejaVuSans", "C:/Projects/fetal-monitor/ml-service/fonts/DejaVuSans.ttf"),
                ("DejaVuSans-Bold", "C:/Projects/fetal-monitor/ml-service/fonts/DejaVuSans-Bold.ttf"),
                
                # 3. Шрифты Liberation
                ("LiberationSans", "fonts/LiberationSans-Regular.ttf"),
                ("LiberationSans-Bold", "fonts/LiberationSans-Bold.ttf"),
                
                # 4. Системные шрифты Windows
                ("Arial", "C:/Windows/Fonts/arial.ttf"),
                ("Arial-Bold", "C:/Windows/Fonts/arialbd.ttf"),
                
                # 5. Системные шрифты Linux
                ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                ("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ]
            
            registered_fonts = []
            
            for font_name, font_path in font_paths:
                if os.path.exists(font_path):
                    try:
                        pdfmetrics.registerFont(TTFont(font_name, font_path))
                        registered_fonts.append(font_name)
                        print(f"✅ Успешно зарегистрирован шрифт: {font_name} из {font_path}")
                    except Exception as e:
                        print(f"⚠️ Не удалось зарегистрировать шрифт {font_path}: {e}")
                        continue
            
            if registered_fonts:
                self.fonts_registered = True
                print(f"✅ Зарегистрированы шрифты: {', '.join(registered_fonts)}")
                
                # Определяем основные шрифты для использования
                if 'DejaVuSans' in registered_fonts and 'DejaVuSans-Bold' in registered_fonts:
                    self.normal_font = 'DejaVuSans'
                    self.bold_font = 'DejaVuSans-Bold'
                elif 'Arial' in registered_fonts and 'Arial-Bold' in registered_fonts:
                    self.normal_font = 'Arial'
                    self.bold_font = 'Arial-Bold'
                elif 'LiberationSans' in registered_fonts and 'LiberationSans-Bold' in registered_fonts:
                    self.normal_font = 'LiberationSans'
                    self.bold_font = 'LiberationSans-Bold'
                else:
                    # Используем первый зарегистрированный шрифт
                    self.normal_font = registered_fonts[0]
                    self.bold_font = registered_fonts[0]
            else:
                print("❌ Не удалось зарегистрировать ни один шрифт с поддержкой кириллицы")
                self.normal_font = 'Helvetica'
                self.bold_font = 'Helvetica-Bold'
                
        except Exception as e:
            print(f"❌ Критическая ошибка при регистрации шрифтов: {e}")
            self.normal_font = 'Helvetica'
            self.bold_font = 'Helvetica-Bold'
            self.fonts_registered = False

    def _create_russian_styles(self):
        """Создает стили с поддержкой русского языка"""
        styles = getSampleStyleSheet()
        
        # Стиль для заголовка
        title_style = ParagraphStyle(
            'RussianTitle',
            parent=styles['Heading1'],
            fontName=self.bold_font,
            fontSize=16,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=1  # CENTER
        )
        
        # Стиль для подзаголовков
        heading_style = ParagraphStyle(
            'RussianHeading',
            parent=styles['Heading2'],
            fontName=self.bold_font,
            fontSize=12,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # Стиль для обычного текста
        normal_style = ParagraphStyle(
            'RussianNormal',
            parent=styles['Normal'],
            fontName=self.normal_font,
            fontSize=10,
            spaceAfter=6
        )
        
        # Стиль для таблиц
        table_style = ParagraphStyle(
            'RussianTable',
            parent=styles['Normal'],
            fontName=self.normal_font,
            fontSize=9
        )
        
        return {
            'title': title_style,
            'heading': heading_style,
            'normal': normal_style,
            'table': table_style
        }
    
    def _safe_text(self, text: Any) -> str:
        """Безопасно конвертирует текст в строку"""
        if text is None:
            return "—"
        return str(text)
    
    def generate_session_report(self, session_data: Dict[str, Any], 
                              analysis_data: Dict[str, Any],
                              patient_info: Dict[str, Any]) -> str:
        """
        Генерирует PDF отчет по сессии на русском языке.
        """
        try:
            # Создаем имя файла
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = session_data.get('session_id', 'unknown')
            filename = f"session_report_{session_id}_{timestamp}.pdf"
            filepath = self.output_dir / filename
            
            print(f"🔄 Начинаем генерацию отчета для сессии {session_id}...")
            print(f"📊 Используем шрифты: normal={self.normal_font}, bold={self.bold_font}")
            
            # Создаем PDF документ
            doc = SimpleDocTemplate(
                str(filepath), 
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            # Получаем стили
            styles = self._create_russian_styles()
            
            # Собираем содержимое отчета
            story = []
            
            # Заголовок
            story.append(Paragraph("ОТЧЕТ ПО СЕССИИ МОНИТОРИНГА ПЛОДА", styles['title']))
            story.append(Spacer(1, 20))
            
            # Информация о сессии
            story.append(Paragraph("ИНФОРМАЦИЯ О СЕССИИ", styles['heading']))
            session_info_data = [
                ["ID сессии:", self._safe_text(session_data.get('session_id'))],
                ["Группа:", self._safe_text(session_data.get('group'))],
                ["Папка:", self._safe_text(session_data.get('folder_id'))],
                ["Дата генерации:", datetime.now().strftime("%d.%m.%Y %H:%M")],
                ["Длительность сессии:", f"{analysis_data.get('features', {}).get('duration_seconds', 0):.1f} сек"],
                ["Всего точек данных:", str(analysis_data.get('features', {}).get('total_samples', 0))]
            ]
            
            session_table = Table(session_info_data, colWidths=[5*cm, 9*cm])
            session_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.normal_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F0F8FF")),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(session_table)
            story.append(Spacer(1, 20))
            
            # Информация о пациентке
            story.append(Paragraph("ИНФОРМАЦИЯ О ПАЦИЕНТКЕ", styles['heading']))
            patient_data = [
                ["Возраст:", f"{self._safe_text(patient_info.get('age'))} лет"],
                ["Срок беременности:", f"{self._safe_text(patient_info.get('gestation_weeks'))} недель"],
                ["pH крови:", self._safe_text(patient_info.get('Ph'))],
                ["Глюкоза:", f"{self._safe_text(patient_info.get('Glu'))} mmol/L"],
                ["Лактат:", f"{self._safe_text(patient_info.get('LAC'))} mmol/L"],
                ["BE:", self._safe_text(patient_info.get('BE'))]
            ]
            
            patient_table = Table(patient_data, colWidths=[5*cm, 9*cm])
            patient_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#A23B72")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.normal_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F8F0FF")),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(patient_table)
            
            # Факторы риска
            risk_factors = patient_info.get('risk_factors', {})
            active_risks = [factor for factor, active in risk_factors.items() if active]
            if active_risks:
                story.append(Spacer(1, 10))
                story.append(Paragraph("ФАКТОРЫ РИСКА:", styles['heading']))
                risks_text = ", ".join(active_risks)
                story.append(Paragraph(risks_text, styles['normal']))
            
            story.append(Spacer(1, 20))
            
            # Статистика BPM
            story.append(Paragraph("СТАТИСТИКА СЕРДЕЧНОГО РИТМА ПЛОДА", styles['heading']))
            features = analysis_data.get('features', {})
            bpm_stats = [
                ["Параметр", "Значение"],
                ["Средний BPM", f"{features.get('mean_bpm', 0):.1f}"],
                ["Медианный BPM", f"{features.get('median_bpm', 0):.1f}"],
                ["Максимальный BPM", f"{features.get('max_bpm', 0):.1f}"],
                ["Минимальный BPM", f"{features.get('min_bpm', 0):.1f}"],
                ["Стандартное отклонение", f"{features.get('std_bpm', 0):.1f}"],
                ["Всего точек BPM", str(features.get('bpm_samples', 0))]
            ]
            
            stats_table = Table(bpm_stats, colWidths=[6*cm, 8*cm])
            stats_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#18A999")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), self.normal_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F0FFF8")),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(stats_table)
            story.append(Spacer(1, 20))
            
            # События
            story.append(Paragraph("СОБЫТИЯ И АНОМАЛИИ", styles['heading']))
            events_data = [
                ["Тип события", "Количество"],
                ["Децелерации", str(features.get('decel_count', 0))],
                ["Эпизоды тахикардии", str(features.get('tachy_count', 0))],
                ["Эпизоды брадикардии", str(features.get('brady_count', 0))]
            ]
            
            events_table = Table(events_data, colWidths=[6*cm, 8*cm])
            events_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F24236")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, -1), self.normal_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#FFF0F0")),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(events_table)
            
            # Заключение
            story.append(Spacer(1, 20))
            story.append(Paragraph("ЗАКЛЮЧЕНИЕ", styles['heading']))
            
            conclusion = self._generate_conclusion(features, patient_info)
            story.append(Paragraph(conclusion, styles['normal']))
            
            # Подпись
            story.append(Spacer(1, 30))
            story.append(Paragraph("Отчет сгенерирован автоматически системой мониторинга плода", 
                                 ParagraphStyle('Footer', parent=styles['normal'], fontSize=8, textColor=colors.gray)))
            
            # Собираем PDF
            print("📄 Собираем PDF документ...")
            doc.build(story)
            print(f"✅ Отчет успешно создан: {filepath}")
            
            return str(filepath)
            
        except Exception as e:
            print(f"❌ Ошибка при генерации PDF: {e}")
            # Пробуем создать резервный PDF
            return self._generate_fallback_pdf(session_data, analysis_data, patient_info)
    
    def _generate_fallback_pdf(self, session_data: Dict, analysis_data: Dict, patient_info: Dict) -> str:
        """Создает резервный PDF если основной метод не работает"""
        from reportlab.pdfgen import canvas
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = session_data.get('session_id', 'unknown')
        filename = f"session_report_{session_id}_{timestamp}_fallback.pdf"
        filepath = self.output_dir / filename
        
        print("🔄 Создаем резервный PDF отчет...")
        
        c = canvas.Canvas(str(filepath), pagesize=A4)
        width, height = A4
        
        # Заголовок
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, height - 100, "FETAL MONITORING REPORT")
        c.setFont("Helvetica", 10)
        
        y_position = height - 140
        
        # Session Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y_position, "SESSION INFORMATION:")
        y_position -= 20
        c.setFont("Helvetica", 10)
        
        session_info = [
            f"Session ID: {session_data.get('session_id', '—')}",
            f"Group: {session_data.get('group', '—')}",
            f"Folder: {session_data.get('folder_id', '—')}",
            f"Date: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            f"Duration: {analysis_data.get('features', {}).get('duration_seconds', 0):.1f} sec",
            f"Samples: {analysis_data.get('features', {}).get('total_samples', 0)}"
        ]
        
        for line in session_info:
            c.drawString(120, y_position, line)
            y_position -= 15
        
        y_position -= 10
        
        # Patient Information
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y_position, "PATIENT INFORMATION:")
        y_position -= 20
        c.setFont("Helvetica", 10)
        
        patient_data = [
            f"Age: {patient_info.get('age', '—')} years",
            f"Gestation: {patient_info.get('gestation_weeks', '—')} weeks",
            f"Blood pH: {patient_info.get('Ph', '—')}",
            f"Glucose: {patient_info.get('Glu', '—')} mmol/L",
            f"Lactate: {patient_info.get('LAC', '—')} mmol/L",
            f"BE: {patient_info.get('BE', '—')}"
        ]
        
        for line in patient_data:
            c.drawString(120, y_position, line)
            y_position -= 15
        
        c.save()
        print(f"✅ Резервный отчет создан: {filepath}")
        return str(filepath)
    
    def _generate_conclusion(self, features: Dict[str, Any], patient_info: Dict[str, Any]) -> str:
        """Генерирует автоматическое заключение на основе данных"""
        conclusions = []
        
        # Анализ BPM
        mean_bpm = features.get('mean_bpm')
        if mean_bpm:
            if mean_bpm > 160:
                conclusions.append("Отмечается устойчивая тахикардия.")
            elif mean_bpm < 110:
                conclusions.append("Наблюдается брадикардия.")
            else:
                conclusions.append("Базальный ритм в пределах нормы.")
        
        # Анализ вариабельности
        std_bpm = features.get('std_bpm')
        if std_bpm:
            if std_bpm < 5:
                conclusions.append("Вариабельность сердечного ритма снижена.")
            elif std_bpm > 15:
                conclusions.append("Вариабельность сердечного ритма повышена.")
            else:
                conclusions.append("Вариабельность сердечного ритма в норме.")
        
        # Анализ событий
        if features.get('decel_count', 0) > 0:
            conclusions.append("Зарегистрированы децелерации.")
        
        if features.get('tachy_count', 0) > 5:
            conclusions.append("Множественные эпизоды тахикардии.")
        
        if features.get('brady_count', 0) > 0:
            conclusions.append("Зарегистрированы эпизоды брадикардии.")
        
        # Анализ факторов риска
        risk_factors = patient_info.get('risk_factors', {})
        active_risks = [factor for factor, active in risk_factors.items() if active]
        if active_risks:
            conclusions.append(f"Присутствуют факторы риска: {', '.join(active_risks)}.")
        
        if not conclusions:
            conclusions.append("Патологических изменений не выявлено. Кардиотокограмма в норме.")
        
        return " ".join(conclusions)

# Глобальный экземпляр генератора отчетов
report_generator = PDFReportGenerator()