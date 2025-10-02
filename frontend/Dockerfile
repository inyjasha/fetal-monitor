FROM nginx:alpine

# Копируем статические файлы
COPY static /usr/share/nginx/html/static
COPY templates /usr/share/nginx/html/templates

# Копируем конфигурацию nginx
COPY nginx.conf /etc/nginx/nginx.conf

# Создаем симлинки для правильной работы маршрутизации
RUN ln -sf /usr/share/nginx/html/templates/main.html /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]