// Переменные для хранения данных и состояния
let monitoringInterval;
let dataInterval;
let monitoringTime = 0;
let isMonitoring = false;
let websocket = null;

let currentSessionId = null;
let currentSessionType = null;

// Данные для графиков
let heartRateData = [];
let contractionsData = [];
const maxDataPoints = 1000;

// Новые переменные для загрузки КГТ
let isKGTLoaded = false;
let loadedKGTData = null;
let kgtPlaybackInterval = null;
let currentPlaybackIndex = 0;
let isPlaybackPaused = false;

// Переменные для аналитики
let currentTrend = null;
let currentRisk = null;
let currentStats = null;

// Данные для отчета
let sessionDataForReport = {
    heartRate: [],
    contractions: [],
    timestamps: [],
    startTime: null,
    endTime: null,
    duration: 0,
    meta: null
};

// Получение элементов canvas
const heartRateCanvas = document.getElementById('heartRateChart');
const contractionsCanvas = document.getElementById('contractionsChart');

// Данные истории КГТ (в реальном приложении будут загружаться с сервера)
const kgtHistoryData = [
    {
        id: 1,
        date: "15.12.2023",
        duration: "60 минут",
        data: generateHistoricalKGTData(60) // 60 минут данных
    },
    {
        id: 2,
        date: "10.12.2023",
        duration: "45 минут",
        data: generateHistoricalKGTData(45) // 45 минут данных
    },
    {
        id: 3,
        date: "05.12.2023",
        duration: "30 минут",
        data: generateHistoricalKGTData(30) // 30 минут данных
    }
];

// Генерация исторических данных КГТ
function generateHistoricalKGTData(durationMinutes) {
    const data = [];
    const dataPoints = durationMinutes * 2; // По одному значению каждые 30 секунд

    for (let i = 0; i < dataPoints; i++) {
        // ЧСС плода с некоторой вариабельностью
        let heartRate = 140 + Math.sin(i * 0.1) * 10 + Math.random() * 5 - 2.5;
        heartRate = Math.round(heartRate);

        // Маточные сокращения с периодами активности
        let contractions = Math.max(0, Math.sin(i * 0.05) * 25 + Math.random() * 10);
        contractions = Math.round(contractions * 10) / 10;

        data.push({
            heartRate,
            contractions,
            timestamp: i * 30 // в секундах
        });
    }

    return data;
}

// Настройка размеров canvas
function setupCanvases() {
    const heartRateCanvas = document.getElementById('heartRateChart');
    const contractionsCanvas = document.getElementById('contractionsChart');
    
    // Получаем реальные размеры контейнеров
    const heartRateContainer = heartRateCanvas.parentElement;
    const contractionsContainer = contractionsCanvas.parentElement;
    
    // Устанавливаем размеры canvas равными размерам контейнеров
    heartRateCanvas.width = heartRateContainer.clientWidth - 40; // Учитываем padding
    heartRateCanvas.height = heartRateContainer.clientHeight - 50; // Учитываем заголовок
    
    contractionsCanvas.width = contractionsContainer.clientWidth - 40;
    contractionsCanvas.height = contractionsContainer.clientHeight - 50;
    
    console.log(`📏 Размеры графиков: ЧСС=${heartRateCanvas.width}x${heartRateCanvas.height}, Сокращения=${contractionsCanvas.width}x${contractionsCanvas.height}`);
}

// Инициализация графиков
function initCharts() {
    setupCanvases();
    drawEmptyChart(heartRateCanvas, 'ЧСС плода');
    drawEmptyChart(contractionsCanvas, 'Маточные сокращения');
}

// Отрисовка пустого графика
function drawEmptyChart(canvas, title) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Очистка canvas
    ctx.clearRect(0, 0, width, height);

    // Рисование сетки
    ctx.strokeStyle = '#333333';
    ctx.lineWidth = 1;

    // Горизонтальные линии
    for (let i = 0; i <= 5; i++) {
        const y = i * height / 5;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // Вертикальные линии (время)
    for (let i = 0; i <= 10; i++) {
        const x = i * width / 10;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }

    // Текст "Ожидание данных"
    ctx.fillStyle = '#888888';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Ожидание данных...', width / 2, height / 2);
}

// Отрисовка графика с данными
function drawChart(canvas, data, color, title) {
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // Очистка canvas
    ctx.clearRect(0, 0, width, height);

    if (data.length < 2) {
        // Рисуем сообщение об ожидании данных
        ctx.fillStyle = '#888888';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Ожидание данных...', width / 2, height / 2);
        return;
    }

    // Рисование сетки - более тонкая и аккуратная
    ctx.strokeStyle = '#444444';
    ctx.lineWidth = 0.5;
    ctx.setLineDash([]);

    // Горизонтальные линии
    for (let i = 0; i <= 5; i++) {
        const y = i * height / 5;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // Вертикальные линии (время) - больше линий для лучшей читаемости
    for (let i = 0; i <= 10; i++) {
        const x = i * width / 10;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }

    // ФИКСИРОВАННЫЙ МАСШТАБ для лучшей читаемости
    let yMin, yMax;
    if (title === 'ЧСС плода') {
        yMin = 80;   // Минимальное значение на графике
        yMax = 200;  // Максимальное значение на графике
    } else {
        // Для сокращений 0-100
        yMin = 0;
        yMax = 100;
    }

    // Рисование данных - более толстая и плавная линия
    ctx.strokeStyle = color;
    ctx.lineWidth = 2.5; // Увеличиваем толщину линии
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.beginPath();

    const xStep = width / (maxDataPoints - 1);

    for (let i = 0; i < data.length; i++) {
        const x = i * xStep;
        
        // ОГРАНИЧИВАЕМ значения чтобы не ломать масштаб
        const clampedValue = Math.max(yMin, Math.min(yMax, data[i]));
        
        // Нормализация с фиксированным масштабом
        const y = height - ((clampedValue - yMin) / (yMax - yMin)) * height;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }

    ctx.stroke();

    // Подписи масштаба для ЧСС - улучшенная читаемость
    if (title === 'ЧСС плода') {
        ctx.fillStyle = '#cccccc';
        ctx.font = '12px Arial';
        ctx.textAlign = 'right';
        
        // Левая шкала - значения ЧСС
        ctx.fillText(yMax.toString(), 35, 15);
        ctx.fillText(Math.round((yMax + yMin) / 2).toString(), 35, height / 2 + 5);
        ctx.fillText(yMin.toString(), 35, height - 5);
        
        // Добавить зеленую зону нормальных значений (110-160)
        const normalMinY = height - ((160 - yMin) / (yMax - yMin)) * height;
        const normalMaxY = height - ((110 - yMin) / (yMax - yMin)) * height;
        
        ctx.fillStyle = 'rgba(0, 255, 0, 0.15)';
        ctx.fillRect(40, normalMinY, width - 50, normalMaxY - normalMinY);
        
        // Подпись нормальной зоны
        ctx.fillStyle = 'rgba(0, 255, 0, 0.7)';
        ctx.font = '10px Arial';
        ctx.textAlign = 'left';
        ctx.fillText('Норма: 110-160 уд/мин', 45, normalMinY - 5);
    }

    // Добавляем текущее значение в правом верхнем углу
    if (data.length > 0) {
        const currentValue = data[data.length - 1];
        ctx.fillStyle = color;
        ctx.font = 'bold 14px Arial';
        ctx.textAlign = 'right';
        ctx.fillText(`${Math.round(currentValue)}`, width - 10, 20);
    }
}

// Обработка изменения размера окна с улучшенной логикой
window.addEventListener('resize', function() {
    console.log('🔄 Изменение размера окна - перерисовка графиков');
    setupCanvases();
    
    if (isMonitoring || isKGTLoaded) {
        // Небольшая задержка для стабилизации размеров
        setTimeout(() => {
            drawChart(heartRateCanvas, heartRateData, '#00ff00', 'ЧСС плода');
            drawChart(contractionsCanvas, contractionsData, '#ff0000', 'Маточные сокращения');
        }, 100);
    } else {
        initCharts();
    }
});

// Обновление аналитики на основе данных от сервера
function updateAnalytics(predictionData) {
    if (!predictionData) return;

    // Обновляем тренд
    if (predictionData.trend) {
        currentTrend = predictionData.trend;
        document.getElementById('trendValue').textContent = 
            predictionData.trend.trend === 'rising' ? '📈 Растет' :
            predictionData.trend.trend === 'falling' ? '📉 Падает' : '➡️ Стабильно';
        
        document.getElementById('trendDirection').textContent = 
            predictionData.trend.trend === 'rising' ? 'Рост' :
            predictionData.trend.trend === 'falling' ? 'Снижение' : 'Стабильный';
        
        document.getElementById('trendDirection').className = 
            `trend-direction ${predictionData.trend.trend}`;
        
        document.getElementById('confidenceValue').textContent = 
            `${Math.round(predictionData.trend.confidence * 100)}%`;
    }

    // Обновляем оценку риска
    if (predictionData.risk) {
        currentRisk = predictionData.risk;
        const riskLevel = predictionData.risk.risk_level;
        
        document.getElementById('riskLevel').textContent = 
            riskLevel === 'high' ? 'Высокий' :
            riskLevel === 'medium' ? 'Средний' : 'Низкий';
        
        document.getElementById('riskLevel').className = 
            `analytics-value risk-level ${riskLevel}`;
        
        document.getElementById('riskScore').textContent = 
            predictionData.risk.score.toFixed(2);
        
        document.getElementById('riskFactors').textContent = 
            predictionData.risk.factors.length > 0 ? 
            predictionData.risk.factors.join(', ') : 'Нет факторов риска';
    }

    // Обновляем статистику
    if (predictionData.statistics) {
        currentStats = predictionData.statistics;
        document.getElementById('meanBPM').textContent = 
            predictionData.statistics.mean_bpm_1min ? 
            Math.round(predictionData.statistics.mean_bpm_1min) : '-';
        
        document.getElementById('medianBPM').textContent = 
            predictionData.statistics.median_bpm_1min ? 
            Math.round(predictionData.statistics.median_bpm_1min) : '-';
        
        document.getElementById('variability').textContent = 
            predictionData.risk ? 
            predictionData.risk.variability.toFixed(1) : '-';
    }
}

// Начало реального мониторинга через WebSocket
function startRealTimeMonitoring(sessionId = null) {
    if (isMonitoring) return;

    // Если загружен КГТ, спрашиваем подтверждение
    if (isKGTLoaded) {
        if (!confirm('Загружен исторический КГТ. Начать новый мониторинг? Текущие данные будут потеряны.')) {
            return;
        }
        closeLoadedKGT();
    }

    console.log('Начало реального мониторинга через WebSocket...');

    isMonitoring = true;
    currentSessionType = 'realtime';
    
    // Если sessionId не передан, используем первую доступную сессию
    if (!sessionId) {
        sessionId = '1'; // Заглушка - первая сессия по умолчанию
    }
    
    currentSessionId = sessionId;
    
    // Инициализация данных для отчета
    sessionDataForReport = {
        heartRate: [],
        contractions: [],
        timestamps: [],
        startTime: new Date(),
        endTime: null,
        duration: 0,
        meta: null
    };

    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('loadKgtBtn').disabled = true;
    document.getElementById('saveBtn').disabled = false; // ВКЛЮЧАЕМ кнопку сохранения

    // Сброс данных
    heartRateData = [];
    contractionsData = [];
    monitoringTime = 0;

    // Обновление таймера
    updateTimer();

    // Запуск интервала таймера
    monitoringInterval = setInterval(() => {
        monitoringTime++;
        updateTimer();
    }, 1000);

    // Подключение к WebSocket
    connectWebSocket(sessionId);

    document.getElementById('statusDisplay').textContent = 'Подключение к серверу...';
    document.getElementById('statusDisplay').style.color = '#593e23';
}

// Подключение к WebSocket
// Подключение к WebSocket
// Подключение к WebSocket
function connectWebSocket(sessionId) {
    const sampleRate = 4.0;
    
    websocket = new WebSocket(`ws://localhost:8001/ws/stream/${sessionId}?sample_rate=${sampleRate}`);

    websocket.onopen = function(event) {
        console.log('WebSocket подключен');
        document.getElementById('statusDisplay').textContent = 'Мониторинг начат (режим реального времени)';
        document.getElementById('statusDisplay').style.color = '#593e23';
        
        // ЗАПРОС МЕТРИК - ДОБАВЛЕНО
        // Запрашиваем начальные метрики
        fetch('/api/metrics/simple')
            .then(response => response.json())
            .then(metrics => {
                console.log('📊 Начальные метрики:', metrics);
            })
            .catch(error => {
                console.error('❌ Ошибка загрузки метрик:', error);
            });
        
        // Периодически запрашиваем метрики
        setInterval(() => {
            fetch('/api/metrics/simple')
                .then(response => response.json())
                .then(metrics => {
                    console.log('📊 Текущие метрики:', metrics);
                })
                .catch(error => {
                    console.error('❌ Ошибка загрузки метрик:', error);
                });
        }, 30000); // Каждые 30 секунд
    };

    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        switch(data.type) {
            case 'meta':
                console.log('Метаданные сессии:', data.meta);
                sessionDataForReport.meta = data.meta;
                break;
                
            case 'frame':
                // Обновление данных графиков
                updateRealTimeData(data);
                break;
                
            case 'prediction':
                // Обновление аналитики
                updateAnalytics(data);
                break;
                
            case 'error':
                console.error('Ошибка от сервера:', data.message);
                document.getElementById('statusDisplay').textContent = `Ошибка: ${data.message}`;
                document.getElementById('statusDisplay').style.color = '#ff0000';
                break;
                
            // МОЖЕТЕ ДОБАВИТЬ ОБРАБОТКУ МЕТРИК ОТ СЕРВЕРА
            case 'metrics_update':
                console.log('📊 Обновление метрик от сервера:', data.metrics);
                break;
        }
    };

    websocket.onclose = function(event) {
        console.log('WebSocket отключен');
        if (isMonitoring) {
            document.getElementById('statusDisplay').textContent = 'Соединение с сервером потеряно';
            document.getElementById('statusDisplay').style.color = '#ff0000';
        }
        
        // ОСТАНАВЛИВАЕМ ИНТЕРВАЛ ЗАПРОСА МЕТРИК ПРИ ОТКЛЮЧЕНИИ
        clearInterval(metricsInterval);
    };

    websocket.onerror = function(error) {
        console.error('WebSocket ошибка:', error);
        document.getElementById('statusDisplay').textContent = 'Ошибка подключения к серверу';
        document.getElementById('statusDisplay').style.color = '#ff0000';
    };
}
// Обновление данных в реальном времени из WebSocket
function updateRealTimeData(data) {
    // Обновление текущих значений
    if (data.bpm !== null && data.bpm !== undefined) {
        document.getElementById('currentHeartRate').textContent = Math.round(data.bpm);
        heartRateData.push(data.bpm);
        
        // Сохраняем данные для отчета
        sessionDataForReport.heartRate.push(data.bpm);
        sessionDataForReport.timestamps.push(data.time);
    }
    
    if (data.uterus !== null && data.uterus !== undefined) {
        document.getElementById('currentContractions').textContent = Math.round(data.uterus);
        contractionsData.push(data.uterus);
        
        // Сохраняем данные для отчета
        sessionDataForReport.contractions.push(data.uterus);
    }

    // Ограничение количества точек данных для отображения (но не для отчета)
    if (heartRateData.length > maxDataPoints) {
        heartRateData.shift();
    }
    if (contractionsData.length > maxDataPoints) {
        contractionsData.shift();
    }

    // Перерисовка графиков
    drawChart(heartRateCanvas, heartRateData, '#00ff00', 'ЧСС плода');
    drawChart(contractionsCanvas, contractionsData, '#ff0000', 'Маточные сокращения');

    // Обновление статуса на основе текущих данных
    updateStatusFromRealTimeData(data);
}

// Обновление статуса на основе реальных данных
function updateStatusFromRealTimeData(data) {
    const statusDisplay = document.getElementById('statusDisplay');
    const greenLight = document.getElementById('greenLight');
    const yellowLight = document.getElementById('yellowLight');

    // Сброс индикаторов
    greenLight.classList.add('inactive');
    yellowLight.classList.add('inactive');

    if (data.bpm !== null && data.bpm !== undefined) {
        if (data.bpm < 110 || data.bpm > 160) {
            statusDisplay.textContent = `Опасность: ЧСС плода ${Math.round(data.bpm)} уд/мин (норма 110-160)`;
            statusDisplay.style.color = '#ff0000';
            yellowLight.classList.remove('inactive');
        } else if (data.uterus > 70) {
            statusDisplay.textContent = 'Опасность: Сильные маточные сокращения';
            statusDisplay.style.color = '#ff0000';
            yellowLight.classList.remove('inactive');
        } else {
            statusDisplay.textContent = 'Состояние хорошее';
            statusDisplay.style.color = '#593e23';
            greenLight.classList.remove('inactive');
        }
    }
}

// Остановка мониторинга
function stopMonitoring() {
    if (!isMonitoring && !isKGTLoaded) return;

    console.log('Остановка мониторинга/воспроизведения...');

    // Сохраняем данные сессии перед остановкой
    if (isMonitoring && sessionDataForReport) {
        sessionDataForReport.endTime = new Date();
        sessionDataForReport.duration = monitoringTime;
        console.log('Данные сессии сохранены для отчета:', {
            heartRatePoints: sessionDataForReport.heartRate.length,
            contractionPoints: sessionDataForReport.contractions.length,
            duration: sessionDataForReport.duration
        });
    }

    if (isMonitoring) {
        isMonitoring = false;
        clearInterval(monitoringInterval);
        
        // Закрытие WebSocket соединения
        if (websocket) {
            websocket.close();
            websocket = null;
        }
    }

    if (isKGTLoaded) {
        // Для загруженных сессий не очищаем полностью, только останавливаем
        document.getElementById('stopBtn').disabled = true;
        document.getElementById('loadKgtBtn').disabled = false;
    }

    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    document.getElementById('loadKgtBtn').disabled = false;
    document.getElementById('saveBtn').disabled = false;

    document.getElementById('statusDisplay').textContent = 'Мониторинг остановлен. Данные готовы для отчета.';
    document.getElementById('statusDisplay').style.color = '#593e23';

    // Выключение индикаторов
    document.getElementById('greenLight').classList.add('inactive');
    document.getElementById('yellowLight').classList.add('inactive');
}

// Обновление таймера
function updateTimer() {
    const minutes = Math.floor(monitoringTime / 60);
    const seconds = monitoringTime % 60;
    document.getElementById('timer').textContent =
        `Время: ${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// Сохранение результатов
async function saveResults() {
    try {
        // Проверяем, есть ли данные для отчета
        if (sessionDataForReport.heartRate.length === 0 && (!currentSessionId || !isKGTLoaded)) {
            alert('❌ Нет данных для сохранения отчета. Запустите мониторинг или загрузите КГТ данные.');
            return;
        }

        console.log('Сохранение отчета...', {
            sessionId: currentSessionId,
            sessionType: currentSessionType,
            dataPoints: sessionDataForReport.heartRate.length
        });

        // Показываем диалог для ввода дополнительной информации
        const doctorNotes = prompt('Введите комментарии врача (необязательно):', '');
        const diagnosis = prompt('Введите диагноз (необязательно):', '');

        // Подготавливаем данные для отправки
        const reportData = {
            session_data: {
                session_id: currentSessionId || `local_${Date.now()}`,
                session_type: currentSessionType || 'local',
                start_time: sessionDataForReport.startTime,
                end_time: sessionDataForReport.endTime || new Date(),
                duration: sessionDataForReport.duration || monitoringTime,
                data_points: sessionDataForReport.heartRate.length
            },
            analysis_data: generateAnalysisFromSessionData(),
            patient_info: {
                // В реальном приложении эти данные должны браться из системы
                age: 30,
                gestation_weeks: 32,
                diagnosis: diagnosis || 'Не указан',
                doctor_notes: doctorNotes || ''
            }
        };

        // Отправляем данные на сервер для генерации отчета
        const response = await fetch('/api/generate-report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(reportData)
        });

        if (!response.ok) {
            throw new Error('Ошибка при генерации отчета на сервере');
        }

        // Получаем PDF файл
        const blob = await response.blob();
        
        // Создаем ссылку для скачивания
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // Генерируем имя файла
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const sessionId = currentSessionId || 'local';
        a.download = `kgt_report_${sessionId}_${timestamp}.pdf`;
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showNotification('✅ Отчет успешно сохранен и скачан', 'success');
        
    } catch (error) {
        console.error('Ошибка сохранения отчета:', error);
        
        // Если серверный endpoint не работает, создаем локальный отчет
        if (error.message.includes('сервере') || error.message.includes('fetch')) {
            createLocalReport();
        } else {
            showNotification('❌ Ошибка при сохранении отчета: ' + error.message, 'error');
        }
    }
}

// Генерация анализа из данных сессии
function generateAnalysisFromSessionData() {
    if (sessionDataForReport.heartRate.length === 0) {
        return {
            features: {
                duration_seconds: 0,
                total_samples: 0,
                bpm_samples: 0,
                mean_bpm: 0,
                median_bpm: 0,
                max_bpm: 0,
                min_bpm: 0,
                std_bpm: 0,
                decel_count: 0,
                tachy_count: 0,
                brady_count: 0
            }
        };
    }

    const heartRate = sessionDataForReport.heartRate;
    const meanBPM = heartRate.reduce((a, b) => a + b, 0) / heartRate.length;
    const maxBPM = Math.max(...heartRate);
    const minBPM = Math.min(...heartRate);
    
    // Вычисляем стандартное отклонение
    const squaredDiffs = heartRate.map(value => Math.pow(value - meanBPM, 2));
    const avgSquaredDiff = squaredDiffs.reduce((a, b) => a + b, 0) / heartRate.length;
    const stdBPM = Math.sqrt(avgSquaredDiff);

    // Подсчитываем события
    const tachyCount = heartRate.filter(bpm => bpm > 160).length;
    const bradyCount = heartRate.filter(bpm => bpm < 110).length;

    return {
        features: {
            duration_seconds: sessionDataForReport.duration,
            total_samples: heartRate.length,
            bpm_samples: heartRate.length,
            mean_bpm: Math.round(meanBPM * 10) / 10,
            median_bpm: Math.round(heartRate.sort((a, b) => a - b)[Math.floor(heartRate.length / 2)] * 10) / 10,
            max_bpm: Math.round(maxBPM),
            min_bpm: Math.round(minBPM),
            std_bpm: Math.round(stdBPM * 10) / 10,
            decel_count: 0, // Упрощенная версия
            tachy_count: tachyCount,
            brady_count: bradyCount
        }
    };
}

// Создание локального отчета (запасной вариант)
function createLocalReport() {
    try {
        // Создаем простой текстовый отчет
        const analysis = generateAnalysisFromSessionData();
        const reportText = `
ОТЧЕТ ПО СЕССИИ КГТ

Дата: ${new Date().toLocaleString()}
Длительность: ${Math.round(sessionDataForReport.duration / 60)} минут
Точек данных: ${sessionDataForReport.heartRate.length}

СТАТИСТИКА ЧСС:
- Среднее: ${analysis.features.mean_bpm} уд/мин
- Максимум: ${analysis.features.max_bpm} уд/мин
- Минимум: ${analysis.features.min_bpm} уд/мин
- Стандартное отклонение: ${analysis.features.std_bpm}

СОБЫТИЯ:
- Тахикардия: ${analysis.features.tachy_count} эпизодов
- Брадикардия: ${analysis.features.brady_count} эпизодов

ЗАКЛЮЧЕНИЕ:
${generateConclusion(analysis.features)}
        `;

        // Создаем и скачиваем текстовый файл
        const blob = new Blob([reportText], { type: 'text/plain;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `kgt_report_${currentSessionId || 'local'}_${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        showNotification('✅ Локальный отчет сохранен', 'success');
    } catch (error) {
        console.error('Ошибка создания локального отчета:', error);
        showNotification('❌ Не удалось создать отчет', 'error');
    }
}

// Генерация заключения
function generateConclusion(features) {
    const conclusions = [];
    
    if (features.mean_bpm > 160) {
        conclusions.push("Отмечается устойчивая тахикардия.");
    } else if (features.mean_bpm < 110) {
        conclusions.push("Наблюдается брадикардия.");
    } else {
        conclusions.push("Базальный ритм в пределах нормы.");
    }
    
    if (features.std_bpm < 5) {
        conclusions.push("Вариабельность сердечного ритма снижена.");
    } else if (features.std_bpm > 15) {
        conclusions.push("Вариабельность сердечного ритма повышена.");
    }
    
    if (features.tachy_count > 5) {
        conclusions.push("Множественные эпизоды тахикардии.");
    }
    
    if (features.brady_count > 0) {
        conclusions.push("Зарегистрированы эпизоды брадикардии.");
    }
    
    if (conclusions.length === 0) {
        conclusions.push("Патологических изменений не выявлено. Кардиотокограмма в норме.");
    }
    
    return conclusions.join(' ');
}

// Загрузка истории КГТ при инициализации
function loadKgtHistory() {
    const historyList = document.getElementById('kgtHistoryList');

    if (kgtHistoryData.length === 0) {
        historyList.innerHTML = '<div class="kgt-history-empty">История КГТ отсутствует</div>';
        return;
    }

    historyList.innerHTML = '';

    kgtHistoryData.forEach(kgtRecord => {
        const historyItem = document.createElement('div');
        historyItem.className = 'kgt-history-item';
        historyItem.innerHTML = `
            <div class="kgt-history-date">${kgtRecord.date}</div>
            <div class="kgt-history-duration">${kgtRecord.duration}</div>
        `;

        historyItem.addEventListener('click', () => {
            // Убираем активный класс у всех элементов
            document.querySelectorAll('.kgt-history-item').forEach(item => {
                item.classList.remove('active');
            });
            // Добавляем активный класс текущему элементу
            historyItem.classList.add('active');

            loadKGTData(kgtRecord);
        });

        historyList.appendChild(historyItem);
    });
}

// Загрузка конкретного КГТ из истории
function loadKGTData(kgtRecord) {
    if (isMonitoring) {
        if (!confirm('Мониторинг активен. Загрузить исторические данные? Текущие данные будут потеряны.')) {
            return;
        }
        stopMonitoring();
    }

    loadedKGTData = kgtRecord.data;
    isKGTLoaded = true;
    currentPlaybackIndex = 0;
    isPlaybackPaused = false;
    currentSessionType = 'historical';
    currentSessionId = `historical_${kgtRecord.id}`;

    // Сохраняем данные для отчета
    sessionDataForReport = {
        heartRate: [],
        contractions: [],
        timestamps: [],
        startTime: new Date(),
        endTime: null,
        duration: kgtRecord.duration,
        meta: {
            patient_name: "Исторические данные",
            session_duration: kgtRecord.duration,
            source: "historical"
        }
    };

    // Обновляем информацию о загруженном КГТ
    document.getElementById('loadedKgtInfo').textContent =
        `${kgtRecord.date} • ${kgtRecord.duration}`;
    document.getElementById('kgtInfoBar').style.display = 'flex';

    // Сбрасываем графики
    heartRateData = [];
    contractionsData = [];

    // Обновляем кнопки управления
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('loadKgtBtn').disabled = true;
    document.getElementById('saveBtn').disabled = false; // Включаем кнопку сохранения

    // Запускаем воспроизведение
    startKGTPlayback();
}

// Запуск воспроизведения загруженного КГТ
function startKGTPlayback() {
    if (!loadedKGTData || loadedKGTData.length === 0) return;

    monitoringTime = 0;
    updateTimer();

    document.getElementById('statusDisplay').textContent = 'Воспроизведение КГТ...';
    document.getElementById('statusDisplay').style.color = '#593e23';

    kgtPlaybackInterval = setInterval(() => {
        if (isPlaybackPaused) return;

        if (currentPlaybackIndex < loadedKGTData.length) {
            const dataPoint = loadedKGTData[currentPlaybackIndex];
            updateDataFromPlayback(dataPoint);
            currentPlaybackIndex++;
            monitoringTime = Math.floor(currentPlaybackIndex * 0.5); // 30 секунд на точку
            updateTimer();
        } else {
            // Воспроизведение завершено
            stopKGTPlayback();
            sessionDataForReport.endTime = new Date();
            document.getElementById('statusDisplay').textContent = 'Воспроизведение завершено. Данные готовы для отчета.';
            document.getElementById('statusDisplay').style.color = '#593e23';
        }
    }, 500); // Ускоренное воспроизведение - 0.5 секунды на точку вместо 30
}

// Обновление данных из воспроизведения
function updateDataFromPlayback(dataPoint) {
    // Обновление текущих значений
    document.getElementById('currentHeartRate').textContent = dataPoint.heartRate;
    document.getElementById('currentContractions').textContent = dataPoint.contractions.toFixed(1);

    // Добавление данных в массивы для графиков
    heartRateData.push(dataPoint.heartRate);
    contractionsData.push(dataPoint.contractions);

    // Сохраняем данные для отчета
    sessionDataForReport.heartRate.push(dataPoint.heartRate);
    sessionDataForReport.contractions.push(dataPoint.contractions);
    sessionDataForReport.timestamps.push(dataPoint.timestamp);

    // Ограничение количества точек данных для отображения
    if (heartRateData.length > maxDataPoints) {
        heartRateData.shift();
    }
    if (contractionsData.length > maxDataPoints) {
        contractionsData.shift();
    }

    // Перерисовка графиков
    drawChart(heartRateCanvas, heartRateData, '#00ff00', 'ЧСС плода');
    drawChart(contractionsCanvas, contractionsData, '#ff0000', 'Маточные сокращения');

    // Обновление статуса каждые 10 точек (каждые 5 секунд при воспроизведении)
    if (currentPlaybackIndex % 10 === 0) {
        updateStatusFromRealTimeData({
            bpm: dataPoint.heartRate,
            uterus: dataPoint.contractions
        });
    }

    // Генерация случайных данных для показателей матери
    updateMotherVitals();

    // Генерация заглушек для аналитики при воспроизведении
    if (currentPlaybackIndex % 20 === 0) {
        generateMockAnalytics(dataPoint);
    }
}

// Генерация заглушек аналитики для режима воспроизведения
function generateMockAnalytics(dataPoint) {
    const mockPrediction = {
        trend: {
            trend: Math.random() > 0.7 ? 'rising' : Math.random() > 0.5 ? 'falling' : 'stable',
            confidence: 0.7 + Math.random() * 0.3,
            slope: (Math.random() - 0.5) * 0.1
        },
        risk: {
            risk_level: Math.random() > 0.8 ? 'high' : Math.random() > 0.5 ? 'medium' : 'low',
            score: Math.random() * 0.8,
            factors: Math.random() > 0.7 ? ['tachycardia'] : Math.random() > 0.5 ? ['high_variability'] : [],
            variability: 5 + Math.random() * 10
        },
        statistics: {
            mean_bpm_1min: dataPoint.heartRate + (Math.random() - 0.5) * 5,
            median_bpm_1min: dataPoint.heartRate + (Math.random() - 0.5) * 3
        }
    };
    
    updateAnalytics(mockPrediction);
}

// Обновление показателей матери (случайные значения)
function updateMotherVitals() {
    const pulse = 70 + Math.random() * 20 - 10;
    const spO2 = 96 + Math.random() * 3;
    const bpSystolic = 110 + Math.random() * 20 - 10;
    const bpDiastolic = 70 + Math.random() * 10 - 5;
    const temp = 36.6 + Math.random() * 0.8 - 0.4;

    document.getElementById('motherPulse').textContent = Math.round(pulse);
    document.getElementById('motherSpO2').textContent = Math.round(spO2);
    document.getElementById('motherBP').textContent =
        `${Math.round(bpSystolic)}/${Math.round(bpDiastolic)}`;
    document.getElementById('motherTemp').textContent = temp.toFixed(1);
}

// Остановка воспроизведения КГТ
function stopKGTPlayback() {
    if (kgtPlaybackInterval) {
        clearInterval(kgtPlaybackInterval);
        kgtPlaybackInterval = null;
    }

    document.getElementById('stopBtn').disabled = true;
    document.getElementById('loadKgtBtn').disabled = false;
}

// Закрытие загруженного КГТ
function closeLoadedKGT() {
    if (isMonitoring) {
        stopMonitoring();
    }

    isKGTLoaded = false;
    loadedKGTData = null;
    currentPlaybackIndex = 0;
    currentSessionId = null;
    currentSessionType = null;

    // Очищаем данные отчета
    sessionDataForReport = {
        heartRate: [],
        contractions: [],
        timestamps: [],
        startTime: null,
        endTime: null,
        duration: 0,
        meta: null
    };

    document.getElementById('kgtInfoBar').style.display = 'none';
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    document.getElementById('saveBtn').disabled = true;

    // Сбрасываем активный элемент истории
    document.querySelectorAll('.kgt-history-item').forEach(item => {
        item.classList.remove('active');
    });

    // Очищаем графики
    heartRateData = [];
    contractionsData = [];
    initCharts();

    // Очищаем аналитику
    clearAnalytics();

    document.getElementById('statusDisplay').textContent = 'Загруженный КГТ закрыт';
    document.getElementById('statusDisplay').style.color = '#593e23';

    // Сбрасываем показатели
    document.getElementById('currentHeartRate').textContent = '0';
    document.getElementById('currentContractions').textContent = '0';
    document.getElementById('motherPulse').textContent = '0';
    document.getElementById('motherSpO2').textContent = '0';
    document.getElementById('motherBP').textContent = '0/0';
    document.getElementById('motherTemp').textContent = '0.0';
}

// Очистка аналитики
function clearAnalytics() {
    document.getElementById('trendValue').textContent = '-';
    document.getElementById('trendDirection').textContent = 'Неизвестно';
    document.getElementById('trendDirection').className = 'trend-direction';
    document.getElementById('confidenceValue').textContent = '0%';
    
    document.getElementById('riskLevel').textContent = '-';
    document.getElementById('riskLevel').className = 'analytics-value risk-level';
    document.getElementById('riskScore').textContent = '0.0';
    document.getElementById('riskFactors').textContent = 'Нет данных';
    
    document.getElementById('meanBPM').textContent = '-';
    document.getElementById('medianBPM').textContent = '-';
    document.getElementById('variability').textContent = '-';
}

// Функция показа уведомлений 
function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
        z-index: 1000;
        max-width: 400px;
        word-wrap: break-word;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    `;
    
    switch(type) {
        case 'success':
            notification.style.backgroundColor = '#4CAF50';
            break;
        case 'error':
            notification.style.backgroundColor = '#f44336';
            break;
        case 'info':
            notification.style.backgroundColor = '#2196F3';
            break;
        default:
            notification.style.backgroundColor = '#593e23';
    }
    
    notification.textContent = message;
    document.body.appendChild(notification);
    
    // Автоматически удаляем через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('Страница загружена, инициализация графиков...');
    initCharts();
    loadKgtHistory(); // Загружаем историю КГТ
    clearAnalytics(); // Очищаем аналитику

    // Обработка изменения размера окна
    window.addEventListener('resize', function() {
        console.log('Изменение размера окна');
        if (isMonitoring || isKGTLoaded) {
            drawChart(heartRateCanvas, heartRateData, '#00ff00', 'ЧСС плода');
            drawChart(contractionsCanvas, contractionsData, '#ff0000', 'Маточные сокращения');
        } else {
            initCharts();
        }
    });

    console.log('Элементы страницы готовы');
});

// Функция возврата назад
function goBack() {
    if (isMonitoring || isKGTLoaded) {
        if (confirm((isMonitoring ? 'Мониторинг еще активен. ' : 'Воспроизведение КГТ активен. ') + 'Вы уверены, что хотите выйти?')) {
            stopMonitoring();
            if (isKGTLoaded) {
                closeLoadedKGT();
            }
            window.location.href = '../templates/cards.html';
        }
    } else {
        window.location.href = '../templates/cards.html';
    }
}

// Функция выхода
function logout() {
    if (isMonitoring || isKGTLoaded) {
        if (confirm((isMonitoring ? 'Мониторинг активен. ' : 'Воспроизведение КГТ активен. ') + 'Вы уверены, что хотите выйти?')) {
            stopMonitoring();
            if (isKGTLoaded) {
                closeLoadedKGT();
            }
            window.location.href = '../templates/authorization.html';
        }
    } else {
        if (confirm('Вы уверены, что хотите выйти?')) {
            window.location.href = '../templates/authorization.html';
        }
    }
}

function loadKGTFromDB() {
    // Создаем скрытый input для выбора файла
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.zip,.csv';
    fileInput.style.display = 'none';
    
    fileInput.onchange = function(event) {
        const file = event.target.files[0];
        if (file) {
            uploadKGTFile(file);
        }
    };
    
    document.body.appendChild(fileInput);
    fileInput.click();
    document.body.removeChild(fileInput);
}

// Функция загрузки КГТ файла
async function uploadKGTFile(file) {
    try {
        showNotification('📤 Загрузка файла...', 'info');
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('patient_name', 'Иванова Мария Петровна'); // В реальном приложении брать из данных пациента
        formData.append('session_duration', '30 минут');

        let endpoint = '/api/upload-kgt';
        
        // Определяем тип загрузки по расширению файла
        if (file.name.toLowerCase().endsWith('.zip')) {
            endpoint = '/api/upload-kgt-zip';
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Ошибка сервера: ${response.status} - ${errorText}`);
        }

        const result = await response.json();
        
        if (result.status === 'success') {
            showNotification('✅ Файл успешно загружен', 'success');
            console.log('Сессия создана:', result);
            
            // Запускаем мониторинг загруженной сессии
            startUploadedSessionMonitoring(result.session_id, result);
        } else {
            throw new Error(result.detail || 'Неизвестная ошибка');
        }

    } catch (error) {
        console.error('Ошибка загрузки файла:', error);
        showNotification(`❌ Ошибка загрузки: ${error.message}`, 'error');
    }
}

// Запуск мониторинга загруженной сессии
function startUploadedSessionMonitoring(sessionId, sessionInfo) {
    if (isMonitoring) {
        if (!confirm('Мониторинг активен. Начать воспроизведение загруженного КГТ? Текущие данные будут потеряны.')) {
            return;
        }
        stopMonitoring();
    }

    console.log('Запуск мониторинга загруженной сессии:', sessionId);

    isKGTLoaded = true;
    currentSessionId = sessionId;
    currentSessionType = 'uploaded';

    // Инициализация данных для отчета
    sessionDataForReport = {
        heartRate: [],
        contractions: [],
        timestamps: [],
        startTime: new Date(),
        endTime: null,
        duration: 0,
        meta: {
            patient_name: sessionInfo.patient_name || 'Загруженный пациент',
            session_duration: sessionInfo.duration_seconds ? 
                `${Math.round(sessionInfo.duration_seconds / 60)} минут` : 'Неизвестно',
            source: "file_upload",
            original_filename: sessionInfo.original_filename
        }
    };

    // Обновляем информацию о загруженном КГТ
    document.getElementById('loadedKgtInfo').textContent = 
        `${sessionInfo.patient_name} • ${sessionInfo.data_points} точек данных`;
    document.getElementById('kgtInfoBar').style.display = 'flex';

    // Сбрасываем графики
    heartRateData = [];
    contractionsData = [];

    // Обновляем кнопки управления
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('loadKgtBtn').disabled = true;
    document.getElementById('saveBtn').disabled = false;

    // Подключаемся к WebSocket для загруженной сессии
    connectUploadedSessionWebSocket(sessionId);
}

// WebSocket для загруженных сессий
function connectUploadedSessionWebSocket(sessionId) {
    const sampleRate = 4.0;
    
    websocket = new WebSocket(`ws://localhost:8001/ws/stream/uploaded/${sessionId}?sample_rate=${sampleRate}`);

    websocket.onopen = function(event) {
        console.log('WebSocket для загруженной сессии подключен');
        document.getElementById('statusDisplay').textContent = 'Воспроизведение загруженного КГТ';
        document.getElementById('statusDisplay').style.color = '#593e23';
        isMonitoring = true;
        
        // Запуск таймера
        monitoringTime = 0;
        updateTimer();
        monitoringInterval = setInterval(() => {
            monitoringTime++;
            updateTimer();
        }, 1000);
    };

    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        switch(data.type) {
            case 'meta':
                console.log('Метаданные загруженной сессии:', data.meta);
                if (data.meta && sessionDataForReport) {
                    sessionDataForReport.meta = data.meta;
                }
                break;
                
            case 'frame':
                updateRealTimeData(data);
                break;
                
            case 'prediction':
                updateAnalytics(data);
                break;
                
            case 'error':
                console.error('Ошибка от сервера:', data.message);
                document.getElementById('statusDisplay').textContent = `Ошибка: ${data.message}`;
                document.getElementById('statusDisplay').style.color = '#ff0000';
                break;
        }
    };

    websocket.onclose = function(event) {
        console.log('WebSocket загруженной сессии отключен');
        if (isMonitoring) {
            stopMonitoring();
            document.getElementById('statusDisplay').textContent = 'Воспроизведение завершено';
            document.getElementById('statusDisplay').style.color = '#593e23';
        }
    };

    websocket.onerror = function(error) {
        console.error('WebSocket ошибка:', error);
        document.getElementById('statusDisplay').textContent = 'Ошибка подключения к серверу';
        document.getElementById('statusDisplay').style.color = '#ff0000';
    };
}