// Переменные для хранения данных и состояния
let monitoringInterval;
let dataInterval;
let monitoringTime = 0;
let isMonitoring = false;

// Данные для графиков
let heartRateData = [];
let contractionsData = [];
const maxDataPoints = 100;

// Новые переменные для загрузки КГТ
let isKGTLoaded = false;
let loadedKGTData = null;
let kgtPlaybackInterval = null;
let currentPlaybackIndex = 0;
let isPlaybackPaused = false;

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
    heartRateCanvas.width = heartRateCanvas.offsetWidth;
    heartRateCanvas.height = heartRateCanvas.offsetHeight;
    contractionsCanvas.width = contractionsCanvas.offsetWidth;
    contractionsCanvas.height = contractionsCanvas.offsetHeight;
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

    if (data.length < 2) return;

    // Рисование данных
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.beginPath();

    const xStep = width / (maxDataPoints - 1);

    for (let i = 0; i < data.length; i++) {
        const x = i * xStep;
        let y;

        if (title === 'ЧСС плода') {
            // Нормализация ЧСС (110-160 уд/мин -> 0-height)
            y = height - ((data[i] - 110) / 50) * height;
        } else {
            // Нормализация сокращений (0-100 мм рт.ст. -> 0-height)
            y = height - (data[i] / 100) * height;
        }

        // Ограничение y в пределах canvas
        y = Math.max(0, Math.min(height, y));

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    }

    ctx.stroke();
}

// Генерация случайных данных для симуляции
function generateData() {
    // ЧСС плода (норма 110-160 уд/мин)
    let heartRate = 135 + Math.random() * 20 - 10;
    heartRate = Math.round(heartRate);

    // Маточные сокращения (0-50 мм рт.ст. в норме)
    let contractions = Math.random() * 50;

    // Показатели матери
    const pulse = 70 + Math.random() * 20 - 10;
    const spO2 = 96 + Math.random() * 3;
    const bpSystolic = 110 + Math.random() * 20 - 10;
    const bpDiastolic = 70 + Math.random() * 10 - 5;
    const temp = 36.6 + Math.random() * 0.8 - 0.4;

    return {
        heartRate,
        contractions,
        pulse: Math.round(pulse),
        spO2: Math.round(spO2),
        bp: `${Math.round(bpSystolic)}/${Math.round(bpDiastolic)}`,
        temp: temp.toFixed(1)
    };
}

// Обновление данных на странице
function updateData() {
    const data = generateData();

    // Обновление текущих значений
    document.getElementById('currentHeartRate').textContent = data.heartRate;
    document.getElementById('currentContractions').textContent = Math.round(data.contractions);

    document.getElementById('motherPulse').textContent = data.pulse;
    document.getElementById('motherSpO2').textContent = data.spO2;
    document.getElementById('motherBP').textContent = data.bp;
    document.getElementById('motherTemp').textContent = data.temp;

    // Добавление данных в массивы
    heartRateData.push(data.heartRate);
    contractionsData.push(data.contractions);

    // Ограничение количества точек данных
    if (heartRateData.length > maxDataPoints) {
        heartRateData.shift();
        contractionsData.shift();
    }

    // Перерисовка графиков
    drawChart(heartRateCanvas, heartRateData, '#00ff00', 'ЧСС плода');
    drawChart(contractionsCanvas, contractionsData, '#ff0000', 'Маточные сокращения');

    // Обновление статуса каждые 5 секунд
    if (monitoringTime % 5 === 0) {
        updateStatus(data);
    }
}

// Обновление статуса
function updateStatus(data) {
    const statusDisplay = document.getElementById('statusDisplay');
    const greenLight = document.getElementById('greenLight');
    const yellowLight = document.getElementById('yellowLight');

    // Сброс индикаторов
    greenLight.classList.add('inactive');
    yellowLight.classList.add('inactive');

    // Проверка состояния
    if (data.heartRate < 110 || data.heartRate > 160) {
        statusDisplay.textContent = `Опасность: ЧСС плода ${data.heartRate} уд/мин (норма 110-160)`;
        statusDisplay.style.color = '#ff0000';
        yellowLight.classList.remove('inactive');
    } else if (data.contractions > 70) {
        statusDisplay.textContent = 'Опасность: Сильные маточные сокращения';
        statusDisplay.style.color = '#ff0000';
        yellowLight.classList.remove('inactive');
    } else {
        statusDisplay.textContent = 'Состояние хорошее';
        statusDisplay.style.color = '#593e23';
        greenLight.classList.remove('inactive');
    }
}

// Начало мониторинга
function startMonitoring() {
    if (isMonitoring) return;

    // Если загружен КГТ, спрашиваем подтверждение
    if (isKGTLoaded) {
        if (!confirm('Загружен исторический КГТ. Начать новый мониторинг? Текущие данные будут потеряны.')) {
            return;
        }
        closeLoadedKGT();
    }

    console.log('Начало мониторинга...');

    isMonitoring = true;
    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;
    document.getElementById('loadKgtBtn').disabled = true;
    document.getElementById('saveBtn').disabled = true;

    // Сброс данных
    heartRateData = [];
    contractionsData = [];
    monitoringTime = 0;

    // Обновление таймера
    updateTimer();

    // Запуск интервалов
    monitoringInterval = setInterval(() => {
        monitoringTime++;
        updateTimer();
    }, 1000);

    // НЕМЕДЛЕННОЕ обновление данных
    updateData();

    // Запуск регулярного обновления данных
    dataInterval = setInterval(updateData, 500);

    document.getElementById('statusDisplay').textContent = 'Мониторинг начат...';
    document.getElementById('statusDisplay').style.color = '#593e23';
}

// Остановка мониторинга
function stopMonitoring() {
    if (!isMonitoring && !isKGTLoaded) return;

    console.log('Остановка мониторинга/воспроизведения...');

    if (isMonitoring) {
        isMonitoring = false;
        clearInterval(monitoringInterval);
        clearInterval(dataInterval);
    }

    if (isKGTLoaded) {
        stopKGTPlayback();
    }

    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
    document.getElementById('loadKgtBtn').disabled = false;
    document.getElementById('saveBtn').disabled = false;

    document.getElementById('statusDisplay').textContent = 'Мониторинг остановлен';
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
function saveResults() {
    alert('Результаты КГТ сохранены в базу данных');
    // В реальном приложении здесь будет отправка данных на сервер
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
    document.getElementById('saveBtn').disabled = true;

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
            document.getElementById('statusDisplay').textContent = 'Воспроизведение завершено';
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

    // Ограничение количества точек данных
    if (heartRateData.length > maxDataPoints) {
        heartRateData.shift();
        contractionsData.shift();
    }

    // Перерисовка графиков
    drawChart(heartRateCanvas, heartRateData, '#00ff00', 'ЧСС плода');
    drawChart(contractionsCanvas, contractionsData, '#ff0000', 'Маточные сокращения');

    // Обновление статуса каждые 10 точек (каждые 5 секунд при воспроизведении)
    if (currentPlaybackIndex % 10 === 0) {
        updateStatus(dataPoint);
    }

    // Генерация случайных данных для показателей матери
    updateMotherVitals();
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
    if (kgtPlaybackInterval) {
        stopKGTPlayback();
    }

    isKGTLoaded = false;
    loadedKGTData = null;
    currentPlaybackIndex = 0;

    document.getElementById('kgtInfoBar').style.display = 'none';
    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;

    // Сбрасываем активный элемент истории
    document.querySelectorAll('.kgt-history-item').forEach(item => {
        item.classList.remove('active');
    });

    // Очищаем графики
    heartRateData = [];
    contractionsData = [];
    initCharts();

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

// Загрузка КГТ из базы данных
function loadKGTFromDB() {
    // В реальном приложении здесь будет AJAX-запрос к серверу
    // Для демонстрации используем модальное окно выбора

    const availableKGTs = [
        { id: 1, date: "15.12.2023 14:30", duration: "60 мин", patient: "Иванова М.П." },
        { id: 2, date: "10.12.2023 11:00", duration: "45 мин", patient: "Иванова М.П." },
        { id: 3, date: "05.12.2023 09:30", duration: "30 мин", patient: "Иванова М.П." }
    ];

    let optionsHTML = availableKGTs.map(kgt =>
        `<option value="${kgt.id}">${kgt.date} • ${kgt.duration} • ${kgt.patient}</option>`
    ).join('');

    const kgtId = prompt(`Выберите КГТ для загрузки:\n\n${availableKGTs.map((kgt, index) =>
        `${index + 1}. ${kgt.date} • ${kgt.duration} • ${kgt.patient}`
    ).join('\n')}\n\nВведите номер:`, "1");

    if (kgtId && !isNaN(kgtId) && kgtId >= 1 && kgtId <= availableKGTs.length) {
        const selectedKGT = kgtHistoryData[kgtId - 1];
        if (selectedKGT) {
            // Находим соответствующий элемент в истории и активируем его
            const historyItems = document.querySelectorAll('.kgt-history-item');
            if (historyItems[kgtId - 1]) {
                historyItems[kgtId - 1].click();
            }
        }
    }
}

// Функция возврата назад
function goBack() {
    if (isMonitoring || isKGTLoaded) {
        if (confirm((isMonitoring ? 'Мониторинг еще активен. ' : 'Воспроизведение КГТ активно. ') + 'Вы уверены, что хотите выйти?')) {
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
        if (confirm((isMonitoring ? 'Мониторинг активен. ' : 'Воспроизведение КГТ активно. ') + 'Вы уверены, что хотите выйти?')) {
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

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('Страница загружена, инициализация графиков...');
    initCharts();
    loadKgtHistory(); // Загружаем историю КГТ

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

    // Добавляем обработчики клавиш для управления воспроизведением
    document.addEventListener('keydown', function(e) {
        if (isKGTLoaded) {
            switch(e.key) {
                case ' ': // Пробел - пауза/продолжить
                    e.preventDefault();
                    togglePlaybackPause();
                    break;
                case 'Escape': // Escape - закрыть загруженный КГТ
                    closeLoadedKGT();
                    break;
            }
        }
    });

    console.log('Элементы страницы готовы');
});

// Дополнительные функции управления воспроизведением
function togglePlaybackPause() {
    if (!isKGTLoaded) return;

    isPlaybackPaused = !isPlaybackPaused;

    if (isPlaybackPaused) {
        document.getElementById('statusDisplay').textContent = 'Воспроизведение приостановлено';
    } else {
        document.getElementById('statusDisplay').textContent = 'Воспроизведение КГТ...';
    }
}

// Функция для перемотки вперед/назад (дополнительная функциональность)
function seekPlayback(seconds) {
    if (!isKGTLoaded || !loadedKGTData) return;

    const newIndex = currentPlaybackIndex + (seconds * 2); // 2 точки в минуту
    if (newIndex >= 0 && newIndex < loadedKGTData.length) {
        currentPlaybackIndex = newIndex;
        monitoringTime = Math.floor(currentPlaybackIndex * 0.5);
        updateTimer();

        // Обновляем данные до текущей позиции
        const dataPoint = loadedKGTData[currentPlaybackIndex];
        updateDataFromPlayback(dataPoint);
    }
}

// Функция для экспорта данных КГТ
function exportKGTData() {
    if (!isKGTLoaded && !isMonitoring) {
        alert('Нет данных для экспорта');
        return;
    }

    const dataToExport = isKGTLoaded ? loadedKGTData :
        heartRateData.map((hr, index) => ({
            heartRate: hr,
            contractions: contractionsData[index] || 0,
            timestamp: index * 30
        }));

    // Создаем CSV содержимое
    let csvContent = "Время (сек),ЧСС плода (уд/мин),Сокращения (мм рт.ст.)\n";
    dataToExport.forEach((point, index) => {
        csvContent += `${point.timestamp},${point.heartRate},${point.contractions}\n`;
    });

    // Создаем и скачиваем файл
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", `kgt_data_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    alert('Данные КГТ экспортированы в CSV файл');
}