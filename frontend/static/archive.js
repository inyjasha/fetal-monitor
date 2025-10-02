// Данные приемов (в реальном приложении будут загружаться с сервера)
const appointmentsData = [
    {
        id: 1,
        patientName: "Иванова Мария Петровна",
        patientId: 2,
        patientAge: "32 года",
        pregnancy: "38 недель",
        date: "15.12.2023",
        time: "14:30 - 15:30",
        status: "completed",
        type: "КГТ",
        heartRate: "135-150 уд/мин",
        contractions: "10-15 мм рт.ст.",
        doctorNotes: "Реактивный нестрессовый тест. Патологических децелераций не выявлено.",
        doctor: "Иванов А.С."
    },
    {
        id: 2,
        patientName: "Петрова Анна Сергеевна",
        patientId: 3,
        patientAge: "28 лет",
        pregnancy: "32 недели",
        date: "14.12.2023",
        time: "10:00 - 11:00",
        status: "completed",
        type: "Консультация",
        heartRate: "-",
        contractions: "-",
        doctorNotes: "Плановый осмотр. Жалоб нет.",
        doctor: "Иванов А.С."
    },
    {
        id: 3,
        patientName: "Иванова Мария Петровна",
        patientId: 2,
        patientAge: "32 года",
        pregnancy: "36 недель",
        date: "10.12.2023",
        time: "09:00 - 10:00",
        status: "completed",
        type: "КГТ",
        heartRate: "140-155 уд/мин",
        contractions: "8-12 мм рт.ст.",
        doctorNotes: "Стабильное состояние. Рекомендовано наблюдение.",
        doctor: "Иванов А.С."
    },
    {
        id: 4,
        patientName: "Иванова Мария Петровна",
        patientId: 2,
        patientAge: "32 года",
        pregnancy: "34 недели",
        date: "05.12.2023",
        time: "11:30 - 12:30",
        status: "completed",
        type: "КГТ",
        heartRate: "130-145 уд/мин",
        contractions: "5-10 мм рт.ст.",
        doctorNotes: "Нормальные показатели. Контроль через 2 недели.",
        doctor: "Иванов А.С."
    },
    {
        id: 5,
        patientName: "Сидорова Елена Владимировна",
        patientId: 4,
        patientAge: "35 лет",
        pregnancy: "40 недель",
        date: "16.12.2023",
        time: "09:00 - 10:00",
        status: "scheduled",
        type: "КГТ",
        heartRate: "-",
        contractions: "-",
        doctorNotes: "Запланированный мониторинг перед родами",
        doctor: "Иванов А.С."
    },
    {
        id: 6,
        patientName: "Козлова Ольга Игоревна",
        patientId: 5,
        patientAge: "26 лет",
        pregnancy: "36 недель",
        date: "13.12.2023",
        time: "16:00 - 17:00",
        status: "canceled",
        type: "КГТ",
        heartRate: "-",
        contractions: "-",
        doctorNotes: "Пациентка не явилась",
        doctor: "Иванов А.С."
    },
    {
        id: 7,
        patientName: "Николаева Татьяна Петровна",
        patientId: 6,
        patientAge: "31 год",
        pregnancy: "34 недели",
        date: "12.12.2023",
        time: "11:30 - 12:30",
        status: "completed",
        type: "Осмотр",
        heartRate: "-",
        contractions: "-",
        doctorNotes: "Плановый осмотр. Все показатели в норме.",
        doctor: "Иванов А.С."
    },
    {
        id: 8,
        patientName: "Иванова Мария Петровна",
        patientId: 2,
        patientAge: "32 года",
        pregnancy: "30 недель",
        date: "01.12.2023",
        time: "14:00 - 15:00",
        status: "completed",
        type: "Консультация",
        heartRate: "-",
        contractions: "-",
        doctorNotes: "Консультация по результатам УЗИ",
        doctor: "Иванов А.С."
    }
];

let currentPage = 1;
const appointmentsPerPage = 5;
let filteredAppointments = [...appointmentsData];

// Новые переменные для фильтрации по пациенту
let selectedPatient = null;

// Инициализация страницы
document.addEventListener('DOMContentLoaded', function() {
    // Проверяем, есть ли выбранный пациент в sessionStorage
    const savedPatient = sessionStorage.getItem('selectedPatient');
    if (savedPatient) {
        selectedPatient = JSON.parse(savedPatient);
        showSelectedPatientBar();
        // Очищаем sessionStorage после использования
        sessionStorage.removeItem('selectedPatient');
    }

    loadAppointments();
    updateStats();
    setupEventListeners();
});

// Настройка обработчиков событий
function setupEventListeners() {
    // Фильтр по дате
    document.getElementById('dateFilter').addEventListener('change', function() {
        if (this.value === 'custom') {
            document.getElementById('customDateRange').style.display = 'flex';
        } else {
            document.getElementById('customDateRange').style.display = 'none';
            filterAppointments();
        }
    });

    // Пользовательский период
    document.getElementById('startDate').addEventListener('change', filterAppointments);
    document.getElementById('endDate').addEventListener('change', filterAppointments);

    // Фильтр по статусу
    document.getElementById('statusFilter').addEventListener('change', filterAppointments);

    // Фильтр по типу
    document.getElementById('typeFilter').addEventListener('change', filterAppointments);

    // Поиск
    document.getElementById('archiveSearch').addEventListener('input', debounce(filterAppointments, 300));
    document.getElementById('archiveSearch').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            filterAppointments();
        }
    });
}

// Показать панель выбранного пациента
function showSelectedPatientBar() {
    if (selectedPatient) {
        document.getElementById('selectedPatientName').textContent = selectedPatient.fullName;
        document.getElementById('selectedPatientBar').style.display = 'flex';
        // Автоматически применяем фильтр по пациенту
        filterAppointments();
    }
}

// Очистка фильтра по пациенту
function clearPatientFilter() {
    selectedPatient = null;
    document.getElementById('selectedPatientBar').style.display = 'none';
    filterAppointments();
}

// Загрузка списка приемов
function loadAppointments() {
    const appointmentsList = document.getElementById('appointmentsList');
    const startIndex = (currentPage - 1) * appointmentsPerPage;
    const endIndex = startIndex + appointmentsPerPage;
    const currentAppointments = filteredAppointments.slice(startIndex, endIndex);

    if (currentAppointments.length === 0) {
        appointmentsList.innerHTML = '<div class="no-appointments">Приемы не найдены</div>';
        renderPagination();
        return;
    }

    appointmentsList.innerHTML = '';

    currentAppointments.forEach(appointment => {
        const appointmentCard = document.createElement('div');
        appointmentCard.className = 'appointment-card';
        appointmentCard.innerHTML = createAppointmentCardHTML(appointment);
        appointmentCard.addEventListener('click', () => openAppointmentDetails(appointment.id));
        appointmentsList.appendChild(appointmentCard);
    });

    renderPagination();
}

// Создание HTML для карточки приема
function createAppointmentCardHTML(appointment) {
    const statusClass = `status-${appointment.status}`;
    const statusText = getStatusText(appointment.status);
    const hasKGT = appointment.type === 'КГТ';

    return `
        <div class="appointment-header">
            <div class="patient-info">
                <h3>${appointment.patientName}</h3>
                <div class="patient-details">
                    ${appointment.patientAge}, ${appointment.pregnancy}
                    ${hasKGT ? '<span class="kgt-badge">КГТ</span>' : ''}
                    ${!selectedPatient ? `<span class="appointment-type">${appointment.type}</span>` : ''}
                </div>
            </div>
            <div class="appointment-meta">
                <div class="appointment-date">${appointment.date}</div>
                <div class="appointment-time">${appointment.time}</div>
                <div class="appointment-status ${statusClass}">${statusText}</div>
            </div>
        </div>
        <div class="appointment-details">
            <div class="detail-item">
                <span class="detail-label">Тип приема:</span>
                <span class="detail-value">${appointment.type}</span>
            </div>
            ${hasKGT ? `
            <div class="detail-item">
                <span class="detail-label">ЧСС плода:</span>
                <span class="detail-value">${appointment.heartRate}</span>
            </div>
            <div class="detail-item">
                <span class="detail-label">Сокращения:</span>
                <span class="detail-value">${appointment.contractions}</span>
            </div>
            ` : ''}
            <div class="detail-item">
                <span class="detail-label">Врач:</span>
                <span class="detail-value">${appointment.doctor}</span>
            </div>
        </div>
    `;
}

// Получение текста статуса
function getStatusText(status) {
    const statusMap = {
        'completed': 'Завершен',
        'scheduled': 'Запланирован',
        'canceled': 'Отменен'
    };
    return statusMap[status] || status;
}

// Фильтрация приемов
function filterAppointments() {
    const searchTerm = document.getElementById('archiveSearch').value.toLowerCase();
    const dateFilter = document.getElementById('dateFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    const typeFilter = document.getElementById('typeFilter').value;

    filteredAppointments = appointmentsData.filter(appointment => {
        // Фильтр по выбранному пациенту
        const matchesPatient = !selectedPatient ||
            appointment.patientName === selectedPatient.fullName;

        // Поиск по ФИО
        const matchesSearch = !searchTerm ||
            appointment.patientName.toLowerCase().includes(searchTerm) ||
            appointment.date.includes(searchTerm);

        // Фильтр по статусу
        const matchesStatus = statusFilter === 'all' || appointment.status === statusFilter;

        // Фильтр по типу приема
        const matchesType = typeFilter === 'all' ||
            (typeFilter === 'kgt' && appointment.type === 'КГТ') ||
            (typeFilter === 'consultation' && appointment.type === 'Консультация') ||
            (typeFilter === 'examination' && appointment.type === 'Осмотр');

        // Фильтр по дате
        let matchesDate = true;
        if (dateFilter !== 'all') {
            const appointmentDate = new Date(appointment.date.split('.').reverse().join('-'));
            const today = new Date();

            switch (dateFilter) {
                case 'today':
                    matchesDate = appointmentDate.toDateString() === today.toDateString();
                    break;
                case 'week':
                    const weekAgo = new Date(today);
                    weekAgo.setDate(today.getDate() - 7);
                    matchesDate = appointmentDate >= weekAgo && appointmentDate <= today;
                    break;
                case 'month':
                    const monthAgo = new Date(today);
                    monthAgo.setMonth(today.getMonth() - 1);
                    matchesDate = appointmentDate >= monthAgo && appointmentDate <= today;
                    break;
                case 'custom':
                    const startDate = document.getElementById('startDate').value;
                    const endDate = document.getElementById('endDate').value;
                    if (startDate && endDate) {
                        matchesDate = appointmentDate >= new Date(startDate) &&
                            appointmentDate <= new Date(endDate);
                    }
                    break;
            }
        }

        return matchesPatient && matchesSearch && matchesStatus && matchesType && matchesDate;
    });

    currentPage = 1;
    loadAppointments();
    updateStats();
}

// Обновление статистики
function updateStats() {
    const total = filteredAppointments.length;
    const completed = filteredAppointments.filter(a => a.status === 'completed').length;
    const today = filteredAppointments.filter(a => {
        const appointmentDate = new Date(a.date.split('.').reverse().join('-'));
        const today = new Date();
        return appointmentDate.toDateString() === today.toDateString();
    }).length;
    const kgtProcedures = filteredAppointments.filter(a => a.type === 'КГТ').length;

    document.getElementById('totalAppointments').textContent = total;
    document.getElementById('completedAppointments').textContent = completed;
    document.getElementById('todayAppointments').textContent = today;
    document.getElementById('kgtProcedures').textContent = kgtProcedures;

    // Обновляем заголовок, если выбран пациент
    if (selectedPatient) {
        document.querySelector('.section-title').textContent =
            `История приемов: ${selectedPatient.fullName}`;
    } else {
        document.querySelector('.section-title').textContent = 'Список приемов';
    }
}

// Пагинация
function renderPagination() {
    const pagination = document.getElementById('pagination');
    const totalPages = Math.ceil(filteredAppointments.length / appointmentsPerPage);

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let paginationHTML = '';

    // Кнопка "Назад"
    paginationHTML += `<button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})">←</button>`;

    // Номера страниц
    const maxVisiblePages = 5;
    let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    // Корректируем startPage, если endPage достиг максимума
    startPage = Math.max(1, endPage - maxVisiblePages + 1);

    // Первая страница и многоточие
    if (startPage > 1) {
        paginationHTML += `<button class="pagination-page" onclick="changePage(1)">1</button>`;
        if (startPage > 2) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
    }

    // Основные страницы
    for (let i = startPage; i <= endPage; i++) {
        if (i === currentPage) {
            paginationHTML += `<button class="pagination-page active">${i}</button>`;
        } else {
            paginationHTML += `<button class="pagination-page" onclick="changePage(${i})">${i}</button>`;
        }
    }

    // Последняя страница и многоточие
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<span class="pagination-ellipsis">...</span>`;
        }
        paginationHTML += `<button class="pagination-page" onclick="changePage(${totalPages})">${totalPages}</button>`;
    }

    // Кнопка "Вперед"
    paginationHTML += `<button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})">→</button>`;

    pagination.innerHTML = paginationHTML;
}

function changePage(page) {
    currentPage = page;
    loadAppointments();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Открытие деталей приема
function openAppointmentDetails(appointmentId) {
    const appointment = appointmentsData.find(a => a.id === appointmentId);
    if (appointment) {
        const modalHTML = `
            <div class="modal-overlay" onclick="closeModal()">
                <div class="modal-content" onclick="event.stopPropagation()">
                    <div class="modal-header">
                        <h3>Детали приема</h3>
                        <button class="modal-close" onclick="closeModal()">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="modal-section">
                            <h4>Информация о пациенте</h4>
                            <div class="modal-details">
                                <div class="modal-detail">
                                    <span class="modal-label">Пациент:</span>
                                    <span class="modal-value">${appointment.patientName}</span>
                                </div>
                                <div class="modal-detail">
                                    <span class="modal-label">Возраст:</span>
                                    <span class="modal-value">${appointment.patientAge}</span>
                                </div>
                                <div class="modal-detail">
                                    <span class="modal-label">Беременность:</span>
                                    <span class="modal-value">${appointment.pregnancy}</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="modal-section">
                            <h4>Информация о приеме</h4>
                            <div class="modal-details">
                                <div class="modal-detail">
                                    <span class="modal-label">Дата:</span>
                                    <span class="modal-value">${appointment.date}</span>
                                </div>
                                <div class="modal-detail">
                                    <span class="modal-label">Время:</span>
                                    <span class="modal-value">${appointment.time}</span>
                                </div>
                                <div class="modal-detail">
                                    <span class="modal-label">Тип приема:</span>
                                    <span class="modal-value">${appointment.type}</span>
                                </div>
                                <div class="modal-detail">
                                    <span class="modal-label">Статус:</span>
                                    <span class="modal-value status-${appointment.status}">${getStatusText(appointment.status)}</span>
                                </div>
                                <div class="modal-detail">
                                    <span class="modal-label">Врач:</span>
                                    <span class="modal-value">${appointment.doctor}</span>
                                </div>
                            </div>
                        </div>
                        
                        ${appointment.type === 'КГТ' ? `
                        <div class="modal-section">
                            <h4>Данные КГТ</h4>
                            <div class="modal-details">
                                <div class="modal-detail">
                                    <span class="modal-label">ЧСС плода:</span>
                                    <span class="modal-value">${appointment.heartRate}</span>
                                </div>
                                <div class="modal-detail">
                                    <span class="modal-label">Маточные сокращения:</span>
                                    <span class="modal-value">${appointment.contractions}</span>
                                </div>
                            </div>
                        </div>
                        ` : ''}
                        
                        <div class="modal-section">
                            <h4>Примечания врача</h4>
                            <div class="modal-notes">
                                ${appointment.doctorNotes}
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="modal-btn secondary" onclick="closeModal()">Закрыть</button>
                        <button class="modal-btn primary" onclick="openKGTFromArchive(${appointment.id})" ${appointment.type !== 'КГТ' ? 'disabled' : ''}>Открыть КГТ</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.body.style.overflow = 'hidden';
    }
}

// Закрытие модального окна
function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}

// Открытие КГТ из архива
function openKGTFromArchive(appointmentId) {
    const appointment = appointmentsData.find(a => a.id === appointmentId);
    if (appointment && appointment.type === 'КГТ') {
        // Сохраняем информацию о выбранном КГТ
        sessionStorage.setItem('selectedKGT', JSON.stringify({
            appointmentId: appointment.id,
            patientName: appointment.patientName,
            date: appointment.date
        }));

        // Закрываем модальное окно
        closeModal();

        // Переходим на страницу КГТ
        window.location.href = '../templates/startKGT.html';
    }
}

// Экспорт в Excel
function exportToExcel() {
    if (filteredAppointments.length === 0) {
        alert('Нет данных для экспорта');
        return;
    }

    // Создаем CSV содержимое
    let csvContent = "Дата,Время,Пациент,Тип приема,Статус,ЧСС плода,Сокращения,Врач,Примечания\n";

    filteredAppointments.forEach(appointment => {
        const row = [
            appointment.date,
            appointment.time,
            `"${appointment.patientName}"`,
            appointment.type,
            getStatusText(appointment.status),
            appointment.heartRate,
            appointment.contractions,
            appointment.doctor,
            `"${appointment.doctorNotes}"`
        ].join(',');

        csvContent += row + '\n';
    });

    // Создаем и скачиваем файл
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);

    const fileName = selectedPatient ?
        `архив_${selectedPatient.fullName}_${new Date().toISOString().split('T')[0]}.csv` :
        `архив_приемов_${new Date().toISOString().split('T')[0]}.csv`;

    link.setAttribute("download", fileName);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    alert(`Данные экспортированы в файл: ${fileName}`);
}

// Функция печати
function printAppointments() {
    if (filteredAppointments.length === 0) {
        alert('Нет данных для печати');
        return;
    }

    // Создаем содержимое для печати
    const printContent = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Архив приемов</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .print-header { text-align: center; margin-bottom: 30px; }
                .print-title { font-size: 24px; font-weight: bold; margin-bottom: 10px; }
                .print-subtitle { font-size: 16px; color: #666; }
                .appointment { border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
                .appointment-header { display: flex; justify-content: space-between; margin-bottom: 10px; }
                .patient-name { font-weight: bold; font-size: 18px; }
                .appointment-meta { text-align: right; }
                .appointment-details { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 14px; }
                .detail-item { display: flex; justify-content: space-between; }
                .detail-label { font-weight: bold; }
                @media print {
                    body { margin: 0; }
                    .appointment { break-inside: avoid; }
                }
            </style>
        </head>
        <body>
            <div class="print-header">
                <div class="print-title">Архив приемов</div>
                <div class="print-subtitle">
                    ${selectedPatient ? `Пациент: ${selectedPatient.fullName}` : 'Все пациенты'} | 
                    Дата печати: ${new Date().toLocaleDateString()} |
                    Всего приемов: ${filteredAppointments.length}
                </div>
            </div>
            ${filteredAppointments.map(appointment => `
                <div class="appointment">
                    <div class="appointment-header">
                        <div class="patient-name">${appointment.patientName}</div>
                        <div class="appointment-meta">
                            <div>${appointment.date} ${appointment.time}</div>
                            <div>${appointment.type} • ${getStatusText(appointment.status)}</div>
                        </div>
                    </div>
                    <div class="appointment-details">
                        <div class="detail-item">
                            <span class="detail-label">Возраст:</span>
                            <span>${appointment.patientAge}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Беременность:</span>
                            <span>${appointment.pregnancy}</span>
                        </div>
                        ${appointment.type === 'КГТ' ? `
                        <div class="detail-item">
                            <span class="detail-label">ЧСС плода:</span>
                            <span>${appointment.heartRate}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Сокращения:</span>
                            <span>${appointment.contractions}</span>
                        </div>
                        ` : ''}
                        <div class="detail-item">
                            <span class="detail-label">Врач:</span>
                            <span>${appointment.doctor}</span>
                        </div>
                    </div>
                    ${appointment.doctorNotes ? `
                    <div style="margin-top: 10px; font-size: 14px;">
                        <strong>Примечания:</strong> ${appointment.doctorNotes}
                    </div>
                    ` : ''}
                </div>
            `).join('')}
        </body>
        </html>
    `;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(printContent);
    printWindow.document.close();

    printWindow.onload = function() {
        printWindow.print();
        printWindow.onafterprint = function() {
            printWindow.close();
        };
    };
}

// Функция выхода
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        window.location.href = '../templates/authorization.html';
    }
}

// Вспомогательная функция для задержки поиска
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Обработка клавиши Escape для закрытия модального окна
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeModal();
    }
});