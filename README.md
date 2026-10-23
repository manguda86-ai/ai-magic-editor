# AI MAGIC EDITOR — MVP

A mobile-first starter app for editing videos up to 120 seconds using text or voice commands.

## Included
- Mobile-friendly dark UI
- Upload MP4/MOV video or image
- 120-second video limit
- Browser video preview and duration display
- Voice-to-text command input (browser support required)
- Backend command parser with optional OpenAI API interpretation
- FFmpeg processing for trimming, basic filters, speed, aspect ratio, subtitles, and MP4 export
- Download edited output
- Temporary upload/output storage

## Requirements
- Python 3.10+
- FFmpeg installed and available on PATH
- Internet access for optional AI interpretation / speech-to-text service
- An API key is optional for the basic command parser. For AI interpretation, set `OPENAI_API_KEY` on the server only.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Android/Termux: python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
# Install FFmpeg separately and confirm `ffmpeg -version` works
uvicorn app:app --host 0.0.0.0 --port 8000
```
Open `http://127.0.0.1:8000` on the same device. For online hosting, deploy the Python app on a server that supports FFmpeg and persistent temporary disk.

## Optional AI setup
Set `OPENAI_API_KEY` as a backend environment variable. Do not put it in `static/index.html` or any client-side JavaScript.
The AI is only used to translate natural-language instructions into a constrained edit plan; FFmpeg performs the supported operations.

## MVP limits
- Maximum source video length: 120 seconds.
- MP4 export is available for video uploads.
- Subtitles use a basic transcription placeholder unless subtitle text is supplied in the command. Full automatic transcription requires connecting a speech-to-text service.
- Background removal and advanced generative effects require additional AI services and are not implemented in this MVP.
- Browser microphone support depends on the browser and usually requires HTTPS when deployed.
