AI MAGIC EDITOR — DEPLOY TO RENDER (ANDROID PHONE)

1. Download and extract this ZIP on your phone.
2. In Chrome, sign in to GitHub and create a new repository named ai-magic-editor.
3. Upload the extracted project files into the repository. Keep this structure:
     Dockerfile
     app.py
     requirements.txt
     README.md
     README_DEPLOY_RENDER.txt
     static/index.html
4. Open Render in Chrome and sign in.
5. Create + New > Web Service. Connect GitHub and choose ai-magic-editor.
6. Choose the Free instance plan if it is offered for your account/region.
7. Since the repository includes a Dockerfile, Render should detect Docker as the runtime.
   Do not use a static-site service; choose Web Service.
8. Create the Web Service and wait for the build to finish.
9. Open the assigned https://YOUR-SERVICE.onrender.com URL in Chrome.
10. Test /api/health by opening https://YOUR-SERVICE.onrender.com/api/health.
    The response should include "ok": true and "ffmpeg": true.

OPTIONAL AI:
In Render service settings, add an environment variable:
    OPENAI_API_KEY = your secret API key
Keep it in Render's environment settings only. Never paste it into index.html or a public repository.
AI provider usage may cost money even if hosting is free. The basic command parser works without this key.

FREE HOSTING NOTES:
- Free services may sleep when idle and take time to wake.
- Uploaded/output files are temporary and may be deleted on restart or sleep.
- The app currently limits uploads to 250 MB and videos to 120 seconds.
- Automatic speech-to-text subtitles, background music generation, background removal, and advanced generative effects are not fully implemented in this MVP.
- Keep your API key private. Don't upload .env files or secrets to GitHub.
