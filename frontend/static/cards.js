// Данные пациента (в реальном приложении будут загружаться с сервера)
const patientData = {
    id: 2,
    fullName: "Иванова Мария Петровна",
    birthDate: "22.07.1990",
    passport: "4510 123456",
    snils: "234-567-890 11",
    address: "г. Москва, ул. Ленина, д. 15, кв. 34",
    bloodGroup: "A(II) Rh+",
    pregnancy: "38 недель, первые роды",
    allergy: "Пенициллин, цитрусовые",
    doctorNotes: "Гестационный диабет под контролем. Рекомендована госпитализация на 39 неделе."
};

// Данные последнего КГТ
const lastKgtData = {
    date: "15.12.2023",
    time: "14:30 - 15:30",
    fetalHeartRate: "135-150 уд/мин",
    accelerations: "5 за 20 мин",
    decelerations: "Отсутствуют",
    uterineTone: "10-15 мм рт.ст.",
    doctorNotes: "Реактивный нестрессовый тест. Патологических децелераций не выявлено."
};

// Функция для заполнения данных пациента
function loadPatientData() {
    document.getElementById('patientFullName').textContent = patientData.fullName;
    document.getElementById('birthDate').textContent = `${patientData.birthDate} (${calculateAge(patientData.birthDate)})`;
    document.getElementById('passport').textContent = patientData.passport;
    document.getElementById('snils').textContent = patientData.snils;
    document.getElementById('address').textContent = patientData.address;
    document.getElementById('bloodGroup').textContent = patientData.bloodGroup;
    document.getElementById('pregnancy').textContent = patientData.pregnancy;
    document.getElementById('allergy').textContent = patientData.allergy;
    document.getElementById('doctorNotes').textContent = patientData.doctorNotes;
}

// Функция для расчета возраста
function calculateAge(birthDate) {
    const birth = new Date(birthDate.split('.').reverse().join('-'));
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();

    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
        age--;
    }

    return age;
}

// Функция для заполнения данных КГТ
function loadKgtData() {
    if (lastKgtData) {
        document.getElementById('kgtDate').textContent = lastKgtData.date;
        document.getElementById('kgtTime').textContent = lastKgtData.time;
        document.getElementById('fetalHeartRate').textContent = lastKgtData.fetalHeartRate;
        document.getElementById('accelerations').textContent = lastKgtData.accelerations;
        document.getElementById('decelerations').textContent = lastKgtData.decelerations;
        document.getElementById('uterineTone').textContent = lastKgtData.uterineTone;
        document.getElementById('kgtDoctorNotes').textContent = lastKgtData.doctorNotes;
    }
}

// Функция возврата назад
function goBack() {
    window.location.href = 'searchDone.html';
}

// Функция выхода
function logout() {
    if (confirm('Вы уверены, что хотите выйти?')) {
        window.location.href = '../templates/authorization.html';
    }
}

// Функция показа истории КГТ
function showKgtHistory() {
    alert('Открывается история КГТ пациента');
    // В реальном приложении здесь будет переход на страницу истории КГТ
}

// Функция проведения нового КГТ
function conductNewKgt() {
    window.location.href = '../templates/startKGT.html'
    // В реальном приложении здесь будет переход на страницу проведения КГТ
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    loadPatientData();
    loadKgtData();
});