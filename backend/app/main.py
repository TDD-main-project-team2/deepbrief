from fastapi import FastAPI
from backend.app.api import auth, users, articles, conversations

app = FastAPI()

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(articles.router)
app.include_router(conversations.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}