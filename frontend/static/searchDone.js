// Данные пациентов (в реальном приложении будут приходить с сервера)
const patientsData = [
    {
        id: 1,
        fullName: "Иванов Иван Иванович",
        birthDate: "15.03.1985",
        snils: "123-456-789 00"
    },
    {
        id: 2,
        fullName: "Иванова Мария Петровна",
        birthDate: "22.07.1990",
        snils: "234-567-890 11"
    },
    {
        id: 3,
        fullName: "Иванов Петр Сергеевич",
        birthDate: "03.11.1978",
        snils: "345-678-901 22"
    }
];

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
                    <div class="patient-name">${patient.fullName}</div>
                    <div class="patient-info">
                        <div class="patient-detail"><strong>Дата рождения:</strong> ${patient.birthDate}</div>
                        <div class="patient-detail"><strong>СНИЛС:</strong> ${patient.snils}</div>
                    </div>
                `;
        patientCard.addEventListener('click', () => {
            // В реальном приложении здесь будет переход на страницу пациента
            alert(`Открывается карта пациента: ${patient.fullName}`);
            window.location.href = `../templates/cards.html?patientId=${patient.id}`;
        });
        patientsList.appendChild(patientCard);

    });
}

// Функция поиска
function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput.value.trim();

    if (searchTerm === '') {
        alert('Пожалуйста, введите ФИО пациента');
        return;
    }

    // В реальном приложении здесь будет AJAX-запрос к серверу
    // console.log(`Поиск пациента: ${searchTerm}`);

    // Обновляем заголовок с количеством найденных пациентов
    document.querySelector('.results-title').textContent = `Найдено пациентов: ${patientsData.length}`;

    // Перерисовываем карточки пациентов
    renderPatients();
}

// Функция возврата назад
function goBack() {
    window.location.href = '../templates/main.html';
}

// Функция выхода
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        window.location.href = '../templates/authorization.html';
    }
}

// Обработка нажатия Enter в поле поиска
document.getElementById('searchInput').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        performSearch();
    }
});

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    renderPatients();
});