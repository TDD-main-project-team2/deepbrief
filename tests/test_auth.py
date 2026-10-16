from backend.models.organization import Organization

def test_register(client):
    response = client.post("/auth/register", json={
    "email": "test@example.com",
    "password": "StrongPass123!",
    "nickname": "tester",
})
    
    assert response.status_code == 200