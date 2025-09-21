package main

import (
	"encoding/json"
	"fmt"
	"net/http"
)

type Ping struct {
	Msg string `json:"msg"`
}

func pingHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(Ping{Msg: "pong from go-ingest"})
}

func main() {
	http.HandleFunc("/ping", pingHandler)
	fmt.Println("Go service running on :8080")
	http.ListenAndServe(":8080", nil)
}
