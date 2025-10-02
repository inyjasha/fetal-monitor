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

// Функция поиска
function performSearch() {
    const searchInput = document.querySelector('.search-input');
    const searchTerm = searchInput.value.trim();

    if (searchTerm === '') {
        alert('Пожалуйста, введите ФИО пациента');
        return;
    }

    // Сохраняем поисковый запрос
    localStorage.setItem('searchQuery', searchTerm);
    
    // Переход на страницу результатов с передачей параметра поиска
    window.location.href = `../templates/searchDone.html?search=${encodeURIComponent(searchTerm)}`;
}

// Функция выхода
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        localStorage.clear();
        window.location.href = '../templates/authorization.html';
    }
}

// Обработчики событий
document.addEventListener('DOMContentLoaded', function() {
    loadDoctorInfo();
    
    document.querySelector('.search-btn').addEventListener('click', performSearch);
    
    document.querySelector('.search-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    document.querySelector('.logout-btn').addEventListener('click', logout);
});