import uvicorn
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from utils.database import engine, Base
from utils.auth import auth_router, get_current_user_oauth2
from Class.api.ClassApi import router as class_router
from Parent.api.ParentApi import router as parent_router
from Student.api.StudentApi import router as student_router
from middlewares import setup_middlewares


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ایجاد جداول هنگام استارت سرور
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="FastAPIThirdProject",
    description="ساخت پروژه سوم برای مدیریت مدرسه",
    version="2.0",
    lifespan=lifespan,
)

setup_middlewares(app)

# روترهای عمومی (بدون احراز هویت)
app.include_router(auth_router)

# روترهای محافظت‌شده (نیاز به JWT)
app.include_router(class_router, dependencies=[Depends(get_current_user_oauth2)])
app.include_router(parent_router, dependencies=[Depends(get_current_user_oauth2)])
app.include_router(student_router, dependencies=[Depends(get_current_user_oauth2)])


@app.get("/")
async def root():
    return {"message": "Welcome To The FastAPI School!"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
