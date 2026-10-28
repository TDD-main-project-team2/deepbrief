from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.api import auth, users, articles, conversations, features, admin
from backend.services.auth.auth_service import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidOrganizationCodeError,
    InvalidAdminCodeError,
)

app = FastAPI()


@app.exception_handler(EmailAlreadyExistsError)
async def email_already_exists_handler(
    request: Request,
    exc: EmailAlreadyExistsError,
):
    return JSONResponse(
        status_code=409,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidAdminCodeError)
@app.exception_handler(InvalidOrganizationCodeError)
async def invalid_organization_code_handler(
    request: Request,
    exc: InvalidOrganizationCodeError,
):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvalidCredentialsError)
async def invalid_credentials_handler(
    request: Request,
    exc: InvalidCredentialsError,
):
    return JSONResponse(
        status_code=401,
        content={"detail": str(exc)},
        headers={"WWW-Authenticate": "Bearer"},
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(articles.router)
app.include_router(conversations.router)
app.include_router(features.router)
app.include_router(admin.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
