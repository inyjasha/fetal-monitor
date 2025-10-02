// Обработка поиска пациента
document.querySelector('.search-btn').addEventListener('click', function() {
    const searchInput = document.querySelector('.search-input');
    if (searchInput.value.trim() === '') {
        alert('Пожалуйста, введите ФИО пациента');
    } else {
        alert(`Поиск пациента: ${searchInput.value}`);
        // В реальном приложении здесь будет отправка запроса на сервер
    }
});
document.querySelector('.logout-btn').addEventListener('click', function() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        window.location.href = '../templates/authorization.html';
    }
});

// Обработка нажатия Enter в поле поиска
document.querySelector('.search-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        document.querySelector('.search-btn').click();
    }
});

//
function performSearch() {
    const searchInput = document.querySelector('.search-input');
    const searchTerm = searchInput.value.trim();

    if (searchTerm === '') {
        alert('Пожалуйста, введите ФИО пациента');
        return;
    }

    // Переход на страницу результатов с передачей параметра поиска
    window.location.href = `../templates/searchDone.html?search=${encodeURIComponent(searchTerm)}`;
}

// Обновите обработчики событий
document.querySelector('.search-btn').addEventListener('click', performSearch);
document.querySelector('.search-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        performSearch();
    }
});