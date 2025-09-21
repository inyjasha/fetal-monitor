FROM golang:1.20-alpine
WORKDIR /app
COPY . .
RUN go mod init go-ingest || true
RUN go mod tidy || true
RUN go build -o server main.go
EXPOSE 8080
CMD ["./server"]
