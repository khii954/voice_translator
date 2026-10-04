import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
import speech_recognition as sr
from translate import Translator
from gtts import gTTS
from pydub import AudioSegment

app = FastAPI(title="مترجم خالد الفوري")

templates = Jinja2Templates(directory="templates")
os.makedirs("temp_audio", exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# الترجمة النصية الصوتيّة المباشرة والمستمرة
@app.post("/translate-text")
async def translate_text(
    text: str = Form(...),
    src_lang: str = Form(...),
    dest_lang: str = Form(...)
):
    output_mp3 = f"temp_audio/{uuid.uuid4()}.mp3"
    try:
        src_code = src_lang.split("-")[0].lower()
        dest_code = dest_lang.split("-")[0].lower()

        # الترجمة الفورية
        translator = Translator(from_lang=src_code, to_lang=dest_code)
        translated_text = translator.translate(text)

        # تحويل النص المترجم إلى صوت
        tts = gTTS(text=translated_text, lang=dest_code, slow=False)
        tts.save(output_mp3)

        return JSONResponse({
            "status": "success",
            "translated_text": translated_text,
            "audio_url": f"/get-audio/{os.path.basename(output_mp3)}"
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# ترجمة الملفات الصوتية المسجلة
@app.post("/translate-audio")
async def translate_audio(
    file: UploadFile = File(...),
    src_lang: str = Form(...),
    dest_lang: str = Form(...)
):
    temp_webm = f"temp_audio/{uuid.uuid4()}.webm"
    temp_wav = f"temp_audio/{uuid.uuid4()}.wav"
    output_mp3 = f"temp_audio/{uuid.uuid4()}.mp3"

    try:
        with open(temp_webm, "wb") as buffer:
            buffer.write(await file.read())

        audio = AudioSegment.from_file(temp_webm)
        audio.export(temp_wav, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav) as source:
            audio_data = recognizer.record(source)
            original_text = recognizer.recognize_google(audio_data, language=src_lang)

        src_code = src_lang.split("-")[0].lower()
        dest_code = dest_lang.split("-")[0].lower()

        translator = Translator(from_lang=src_code, to_lang=dest_code)
        translated_text = translator.translate(original_text)

        tts = gTTS(text=translated_text, lang=dest_code, slow=False)
        tts.save(output_mp3)

        if os.path.exists(temp_webm): os.remove(temp_webm)
        if os.path.exists(temp_wav): os.remove(temp_wav)

        return JSONResponse({
            "status": "success",
            "original_text": original_text,
            "translated_text": translated_text,
            "audio_url": f"/get-audio/{os.path.basename(output_mp3)}"
        })

    except sr.UnknownValueError:
        return JSONResponse({"status": "error", "message": "لم يتم التعرف على الصوت بشكل واضح، حاول التحدث بصوت أوضح"}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# جلب وتشغيل الملف الصوتي
@app.get("/get-audio/{filename}")
async def get_audio(filename: str):
    file_path = f"temp_audio/{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    return JSONResponse({"error": "File not found"}, status_code=404)