"""desktop/voice/ — produkcijski Realtime voice runtime (OA-1).

Restrukturirani glasovni sloj iz desktop/ui/voice.py u paket sa odvojenim
odgovornostima (state mašina, guards, event parsing, audio level, session,
worker). Čiste komponente (state/guards/events/audio) su jedinično testabilne
bez stvarnog WebSocket-a ili mikrofona.
"""
