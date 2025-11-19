from fastapi import FastAPI, Depends
from database import engine
import models
# روترها
from Student.api.student_router import router as student_router
from Parent.api.parent_router import router as parent_router
from Class.api.class_router import router as class_router
from utils.auth import router as auth_router, get_current_user

app = FastAPI(
    title="School Management API",
    description="FastApi Third project",
    version="1.0.0"
)

# ساخت جداول
models.Base.metadata.create_all(bind=engine)

# روتر احراز هویت (بدون نیاز به توکن)
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# تمام روترهای اصلی با JWT محافظت شده
app.include_router(
    parent_router,
    prefix="/parents",
    tags=["Parents"],
    dependencies=[Depends(get_current_user)]  # فقط کاربر لاگین‌کرده میتونه دسترسی داشته باشه
)

app.include_router(
    class_router,
    prefix="/classes",
    tags=["Classes"],
    dependencies=[Depends(get_current_user)]
)
# /students/students
app.include_router(
    student_router,
    prefix="/students",
    tags=["Students"],
    dependencies=[Depends(get_current_user)]
)


@app.get("/")
def home():
    return {
        "message": "for better security JWT is activated",
        "login": "POST /auth/login → username: admin, password: admin123",
        "docs": "http://127.0.0.1:8000/docs → press authorize button after logining"
    }



if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True, log_level="info")
