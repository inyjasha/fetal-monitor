document.getElementById('loginForm').addEventListener('submit', function(e) {
    e.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    // Простая проверка для демонстрации
    if (username && password) {
        // Переход на страницу поиска пациента
        window.location.href = 'main.html';
    } else {
        alert('Пожалуйста, введите логин и пароль');
    }
});
