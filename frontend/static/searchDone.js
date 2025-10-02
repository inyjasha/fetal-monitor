// Данные пациентов БУДУТ загружаться из localStorage (результаты поиска с бэкенда)
let patientsData = [];

// Функция для загрузки данных из localStorage
function loadPatientsFromStorage() {
    const storedResults = localStorage.getItem('searchResults');
    const urlParams = new URLSearchParams(window.location.search);
    const searchQuery = urlParams.get('search') || localStorage.getItem('searchQuery') || '';
    
    if (storedResults) {
        patientsData = JSON.parse(storedResults);
        console.log('✅ Загружены данные из бэкенда:', patientsData);
    } else {
        console.log('❌ Нет данных в localStorage, используем пустой массив');
        patientsData = [];
    }
    
    // Устанавливаем значение в поле поиска
    document.getElementById('searchInput').value = searchQuery;
    
    // Если есть поисковый запрос в URL, выполняем поиск
    if (searchQuery && searchQuery.length >= 2) {
        performSearch();
    } else {
        // Обновляем заголовок
        document.querySelector('.results-title').textContent = `Найдено пациентов: ${patientsData.length}`;
        renderPatients();
    }
}

// Функция для отображения карточек пациентов
function renderPatients() {
    const patientsList = document.getElementById('patientsList');
    patientsList.innerHTML = '';

    if (patientsData.length === 0) {
        patientsList.innerHTML = '<div class="no-results">Пациенты не найдены</div>';
        return;
    }

    patientsData.forEach(patient => {
        const patientCard = document.createElement('div');
        patientCard.className = 'patient-card';
        patientCard.innerHTML = `
            <div class="patient-name">${patient.full_name}</div>
            <div class="patient-info">
                <div class="patient-detail"><strong>Возраст:</strong> ${patient.age} лет</div>
                <div class="patient-detail"><strong>Срок беременности:</strong> ${patient.gestation_weeks > 0 ? patient.gestation_weeks + ' недель' : 'Не беременна'}</div>
                <div class="patient-detail"><strong>Последний прием:</strong> ${patient.last_session_date || 'Нет данных'}</div>
                <div class="patient-detail"><strong>Уровень риска:</strong> ${patient.risk_level || 'Не оценен'}</div>
            </div>
        `;
        patientCard.addEventListener('click', () => {
            // Сохраняем выбранного пациента для следующей страницы
            localStorage.setItem('selectedPatient', JSON.stringify(patient));
            // Переход на страницу карты пациента
            window.location.href = `../templates/cards.html?patientId=${patient.patient_id}`;
        });
        patientsList.appendChild(patientCard);
    });
}

// Функция поиска (обновленная - делает запрос к бэкенду)
async function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.trim();

    if (searchTerm === '') {
        alert('Пожалуйста, введите ФИО пациента');
        return;
    }

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`http://localhost:8001/api/patients/search?query=${encodeURIComponent(searchTerm)}&limit=20`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const patients = await response.json();
            
            console.log('🔍 Результаты поиска:', patients);
            
            // Сохраняем результаты в localStorage
            localStorage.setItem('searchResults', JSON.stringify(patients));
            localStorage.setItem('searchQuery', searchTerm);
            
            // Обновляем данные и перерисовываем
            patientsData = patients;
            document.querySelector('.results-title').textContent = `Найдено пациентов: ${patients.length}`;
            renderPatients();
            
        } else if (response.status === 400) {
            const errorData = await response.json();
            alert(`Ошибка поиска: ${errorData.detail}`);
        } else {
            alert('Ошибка поиска пациентов');
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alert('Ошибка соединения с сервером');
    }
}

// Функция возврата назад
function goBack() {
    window.location.href = '../templates/main.html';
}

// Функция выхода
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        localStorage.clear();
        window.location.href = '../templates/authorization.html';
    }
}

// Обработка нажатия Enter в поле поиска
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        performSearch();
    }
});

// Загрузка информации о враче
async function loadDoctorInfo() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '../templates/authorization.html';
            return;
        }

        const response = await fetch('http://localhost:8001/api/auth/me', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (response.ok) {
            const userData = await response.json();
            document.querySelector('.doctor-name').textContent = userData.full_name;
        } else {
            window.location.href = '../templates/authorization.html';
        }
    } catch (error) {
        console.error('Ошибка загрузки данных врача:', error);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadDoctorInfo();
    loadPatientsFromStorage();
});