from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional

app = FastAPI(title="CIS Dashboard Mock API")
security = HTTPBearer()

EXPECTED_TOKEN = "default_cis_token"

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if credentials.credentials != EXPECTED_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Mock Data
MOCK_BRANCHES = [
    {
        "id": "11111111-1111-1111-1111-111111111111",
        "name": "Jakarta Central Clinic",
        "address": "Sudirman St. 12",
        "image_url": "https://example.com/images/clinic1.jpg"
    },
    {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "Bandung Main Clinic",
        "address": "Sucipto St. 12",
        "image_url": "https://example.com/images/clinic2.jpg"
    }
]

MOCK_DOCTORS = [
    {
        "cis_id": "DR-12345",
        "name": "Dr. Jane Doe",
        "email": "jane.doe@example.com",
        "branch_ids": [
            "11111111-1111-1111-1111-111111111111"
        ]
    },
    {
        "cis_id": "DR-67890",
        "name": "Dr. John Smith",
        "email": "john.smith@example.com",
        "branch_ids": [
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222"
        ]
    }
]

@app.get("/api/v1/branches", dependencies=[Depends(verify_token)])
async def get_branches():
    return {"branches": MOCK_BRANCHES}

@app.get("/api/v1/branches/{branch_id}", dependencies=[Depends(verify_token)])
async def get_branch(branch_id: str):
    for b in MOCK_BRANCHES:
        if b["id"] == branch_id:
            return b
    raise HTTPException(status_code=404, detail="Branch not found")

@app.get("/api/v1/doctors", dependencies=[Depends(verify_token)])
async def get_doctors():
    docs_list = []
    for d in MOCK_DOCTORS:
        docs_list.append({
            "doctor_cis_id": d["cis_id"],
            "name": d["name"],
            "email": d["email"]
        })
    return {"doctors": docs_list}

@app.get("/api/v1/doctors/{cis_id}", dependencies=[Depends(verify_token)])
async def get_doctor(cis_id: str):
    for d in MOCK_DOCTORS:
        if d["cis_id"] == cis_id:
            return d
    raise HTTPException(status_code=404, detail="Doctor not found")
