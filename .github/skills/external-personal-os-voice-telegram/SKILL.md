---
name: voice-telegram
description: "Transcribe Telegram voice messages and forward to agents. Use when user sends voice/audio message via Telegram."
---

# Voice Telegram — голосовые сообщения в Telegram

Транскрибирует входящие войсы через faster-whisper и передаёт текст агенту как обычный запрос.

## Как использует Pron

Когда приходит voice message из Telegram:
1. Файл уже скачан в `/Users/abserver/.openclaw/media/inbound/`
2. Транскрибируй через faster-whisper (локально, офлайн)
3. Обработай транскрипт как обычное текстовое сообщение

## Команда транскрипции

```bash
cd ~/Projects/voice-bridge && source .venv/bin/activate && python3 -c "
from stt.faster_whisper import FasterWhisperSTT
import sys, pathlib

path = sys.argv[1]
audio = pathlib.Path(path).read_bytes()
stt = FasterWhisperSTT(model_size='base', language='ru')
result = stt.transcribe(audio)
print(result or '')
" <PATH_TO_FILE>
```

## Superflow + голос

Если транскрипт содержит "superflow" или "суперфлоу" — 
читай ~/clawd/skills/superflow/SKILL.md и запускай фазу 1.
