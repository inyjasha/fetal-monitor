// Данные приемов (в реальном приложении будут загружаться с сервера)
const appointmentsData = [
    {
        id: 1,
        patientName: "Иванова Мария Петровна",
        patientAge: "32 года",
        pregnancy: "38 недель",
        date: "15.12.2023",
        time: "14:30 - 15:30",
        status: "completed",
        type: "КГТ",
        heartRate: "135-150 уд/мин",
        contractions: "10-15 мм рт.ст.",
        doctorNotes: "Реактивный нестрессовый тест",
        doctor: "Иванов А.С."
    },
    {
        id: 2,
        patientName: "Петрова Анна Сергеевна",
        patientAge: "28 лет",
        pregnancy: "32 недели",
        date: "14.12.2023",
        time: "10:00 - 11:00",
        status: "completed",
        type: "Консультация",
        heartRate: "-",
        contractions: "-",
        doctorNotes: "Плановый осмотр",
        doctor: "Иванов А.С."
    },
    {
        id: 3,
        patientName: "Сидорова Елена Владимировна",
        patientAge: "35 лет",
        pregnancy: "40 недель",
        date: "16.12.2023",
        time: "09:00 - 10:00",
        status: "scheduled",
        type: "КГТ",
        heartRate: "-",
        contractions: "-",
        doctorNotes: "Запланированный мониторинг",
        doctor: "Иванов А.С."
    },
    {
        id: 4,
        patientName: "Козлова Ольга Игоревна",
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
        id: 5,
        patientName: "Николаева Татьяна Петровна",
        patientAge: "31 год",
        pregnancy: "34 недели",
        date: "12.12.2023",
        time: "11:30 - 12:30",
        status: "completed",
        type: "КГТ",
        heartRate: "140-155 уд/мин",
        contractions: "8-12 мм рт.ст.",
        doctorNotes: "Стабильное состояние",
        doctor: "Иванов А.С."
    }
];

let currentPage = 1;
const appointmentsPerPage = 5;
let filteredAppointments = [...appointmentsData];

// Инициализация страницы
document.addEventListener('DOMContentLoaded', function() {
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

    // Поиск
    document.getElementById('archiveSearch').addEventListener('input', debounce(filterAppointments, 300));
    document.getElementById('archiveSearch').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            filterAppointments();
        }
    });
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

    filteredAppointments = appointmentsData.filter(appointment => {
        // Поиск по ФИО
        const matchesSearch = !searchTerm ||
            appointment.patientName.toLowerCase().includes(searchTerm) ||
            appointment.date.includes(searchTerm);

        // Фильтр по статусу
        const matchesStatus = statusFilter === 'all' || appointment.status === statusFilter;

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

        return matchesSearch && matchesStatus && matchesDate;
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
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage) {
            paginationHTML += `<button class="pagination-page active">${i}</button>`;
        } else {
            paginationHTML += `<button class="pagination-page" onclick="changePage(${i})">${i}</button>`;
        }
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
        alert(`Детали приема:\n\nПациент: ${appointment.patientName}\nДата: ${appointment.date}\nВремя: ${appointment.time}\nСтатус: ${getStatusText(appointment.status)}\nТип: ${appointment.type}\n\nПримечания: ${appointment.doctorNotes}`);

        // В реальном приложении здесь будет переход на страницу деталей приема
        // window.location.href = `appointment-details.html?id=${appointmentId}`;
    }
}

// Экспорт в Excel
function exportToExcel() {
    alert('Функция экспорта в Excel будет реализована в следующей версии');
    // В реальном приложении здесь будет логика экспорта данных
}

// Поиск в архиве
function performArchiveSearch() {
    filterAppointments();
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