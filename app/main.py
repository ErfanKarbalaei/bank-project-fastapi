from fastapi import FastAPI
from app.db.session import engine

app = FastAPI(title="Banking API", version="1.0.0")


@app.get("/")
def root():
    return {"message": "Banking API is running"}



@app.on_event("startup")
async def startup_event():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(lambda x: None)
        print("Database connected successfully!")
    except Exception as e:
        print("Database connection failed:", e)
