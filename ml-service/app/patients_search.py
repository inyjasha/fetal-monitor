# app/patients_search.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/patients", tags=["patients"])

class PatientSearchResult(BaseModel):
    patient_id: int
    full_name: str
    age: int
    gestation_weeks: int
    last_session_date: Optional[str] = None
    risk_level: Optional[str] = None

# Временная база данных пациентов (заглушка)
patients_db = [
    {"patient_id": 1, "full_name": "Иванова Мария Петровна", "age": 28, "gestation_weeks": 32, "last_session_date": "2024-01-15", "risk_level": "low"},
    {"patient_id": 2, "full_name": "Петрова Анна Сергеевна", "age": 32, "gestation_weeks": 28, "last_session_date": "2024-01-14", "risk_level": "medium"},
    {"patient_id": 3, "full_name": "Сидорова Елена Владимировна", "age": 25, "gestation_weeks": 36, "last_session_date": "2024-01-13", "risk_level": "high"},
    {"patient_id": 4, "full_name": "Козлова Ольга Игоревна", "age": 30, "gestation_weeks": 30, "last_session_date": "2024-01-12", "risk_level": "low"},
    {"patient_id": 5, "full_name": "Троицкая Екатерина Вадимовна", "age": 39, "gestation_weeks": 0, "last_session_date": "2024-01-11", "risk_level": "low"},
    {"patient_id": 6, "full_name": "Краснова Татьяна Федоровна", "age": 46, "gestation_weeks": 0, "last_session_date": "2024-01-10", "risk_level": "medium"},
]

@router.get("/search", response_model=List[PatientSearchResult])
async def search_patients(
    query: str = Query(..., description="ФИО пациента для поиска"),
    limit: int = Query(20, description="Лимит результатов")
):
    if not query or len(query.strip()) < 2:
        raise HTTPException(status_code=400, detail="Слишком короткий поисковый запрос")
    
    search_term = query.lower().strip()
    results = []
    
    for patient in patients_db:
        # Более гибкий поиск - ищем вхождение в любой части ФИО
        if (search_term in patient["full_name"].lower() or
            any(term in patient["full_name"].lower() for term in search_term.split())):
            results.append(PatientSearchResult(**patient))
    
    return results[:limit]

@router.get("/{patient_id}")
async def get_patient_details(patient_id: int):
    for patient in patients_db:
        if patient["patient_id"] == patient_id:
            return patient
    raise HTTPException(status_code=404, detail="Пациент не найден")