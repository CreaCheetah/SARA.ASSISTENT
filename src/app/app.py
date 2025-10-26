from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "SARA backend actief"}

@app.get("/healthz")
def health():
    return {"ok": True}

@app.post("/asr")
async def asr_endpoint(file: UploadFile = File(...), language: str = "nl"):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    text = transcribe_bytes(data, suffix=f".{file.filename.split('.')[-1]}", language=language)
    return {"text": text}
