# FAZA 8 - Voice-first UI refactor

## Datum

2026-07-05

## Scope

Implementirana je samo FAZA 8 iz `docs/MIGRATION_PLAN.md`: voice-first UI refactor oko postojećeg `src/lib/realtime.ts`, centralni `VoiceState`, Realtime Event Router, TopBar/BottomVoiceBar i lokalni Activity/transcript prikaz.

Nije zamijenjen WebRTC/OpenAI Realtime audio pipeline. Nije implementirana FAZA 6 session security. Nije dodavan Python audio, STT, VAD ili TTS.

## GitNexus impact

Prije izmjene pokrenut je GitNexus impact:

- `RickyRealtimeClient` u `src/lib/realtime.ts`: risk `LOW`, direktno utiče na `src/App.tsx`, `src/components/RickyFace.tsx` import i fuzzy `electron/main.cjs` call, bez affected processes.
- `App` u `src/App.tsx`: risk `LOW`, bez upstream dependents.
- `RickyFace`: risk `LOW`; nije mijenjan.

Ručni blast radius: promjene su ograničene na renderer voice UI/state sloj i postojeći Realtime event handling. Backend, Electron toolovi, Python storage i legacy PowerShell nisu mijenjani u ovoj fazi. Nakon implementacije `gitnexus_detect_changes(scope=all)` je prijavio `risk_level: high` jer su promijenjeni centralni voice flow simboli (`App`, `RickyRealtimeClient.connect`, `handleServerEvent`, `executeFunctionCalls`) i 13 voice execution procesa. Ovo je očekivan rizik za FAZU 8 i razlog za dodatno ručno voice smoke testiranje prije commita/release-a.

## Šta je urađeno

- Dodan centralni voice state model:
  - `src/lib/voiceState.ts`
- Dodan Realtime Event Router:
  - `src/lib/realtimeEventRouter.ts`
- `src/lib/realtime.ts` sada:
  - re-exportuje `VoiceState` i `ActivityEvent`
  - prima `onVoiceState` i `onActivity` callbackove
  - mapira raw OpenAI Realtime evente kroz router
  - i dalje zadržava postojeći WebRTC, microphone, audio playback i tool-call tok.
- Dodane voice-first UI komponente:
  - `src/components/VoiceTopBar.tsx`
  - `src/components/BottomVoiceBar.tsx`
  - `src/components/ActivityTimeline.tsx`
- `src/App.tsx` refaktorisan da koristi:
  - `VoiceTopBar`
  - `BottomVoiceBar`
  - lokalni `ActivityTimeline`
  - `VoiceState` pored postojećeg mood/mouth state-a.
- `src/styles.css` dopunjen za:
  - voice state pill/dot
  - top voice bar
  - bottom voice status
  - activity timeline styling
  - stabilne dimenzije kontrole.
- `docs/MIGRATION_PLAN.md` tracker red za FAZU 8 označen kao urađen.

## Zašto je urađeno

Voice-first arhitektura traži da glas bude primarni product surface, a tekst fallback. Ova faza uvodi vidljiv centralni voice state i odvaja raw Realtime event mapping od UI renderovanja bez promjene audio pipeline-a.

## Kako je urađeno

`realtimeEventRouter.ts` prima raw OpenAI event tipove i vraća interni app state/activity:

```text
input_audio_buffer.speech_started -> listening
input_audio_buffer.speech_stopped -> transcribing
conversation.item.input_audio_transcription.completed -> thinking + transcript activity
response.audio.delta -> speaking
response.done -> idle + response completed activity
error -> error
```

`App.tsx` drži lokalni `activityEvents` niz. Ovo još nije backend persistence; to pripada kasnijem Activity/transcript backend toku.

## Šta nije dirano

- Nije mijenjan Realtime WebRTC endpoint ili SDP flow.
- Nije mijenjan mikrofon/audio playback pipeline.
- Nije dodavan Python STT/TTS/VAD.
- Nije mijenjan Electron IPC/preload.
- Nije implementirana FAZA 6.
- Nije implementirana FAZA 9 confirmations/plans.
- Nije mijenjan `RickyFace`.
- Nije diran Python backend osim što su testovi pokrenuti za regresiju.

## Verifikacija

Pokrenuto:

```text
npm run build
python -m pytest
```

Rezultati:

```text
npm run build: prošao
pytest: 11 passed, 1 warning
```

`pytest` warning je postojeći FastAPI/Starlette `TestClient` deprecation warning.

## Rizici/ograničenja

- Activity/transcript prikaz je lokalni renderer state, bez persistence u SQLite. Backend activity/transcript endpointi nisu dio ove implementacije.
- Realtime event mapping pokriva osnovne evente koji postoje u trenutnom `realtime.ts`; dodatni OpenAI raw eventi se ignorišu dok ne budu potrebni.
- UI nije ručno verifikovan u Electron prozoru tokom ove sesije; `npm run build` potvrđuje TypeScript/Vite integritet.
- Worktree je već imao mnogo postojećih dirty izmjena iz prethodnih faza/drugog agenta.

## Potreban follow-up

- FAZA 9 može koristiti `VoiceState` i Activity UI za confirmations/plans prikaz.
- Kasnije treba povezati transcript/activity persistence sa Python backendom kada endpointi budu uvedeni.
- Ako se uvodi true push-to-talk, treba ga raditi bez prepisivanja `src/lib/realtime.ts` audio pipeline-a.

## Potrebna korisnička potvrda

Prije commita treba potvrditi šta ulazi u commit, jer worktree sadrži postojeće izmjene koje nisu dio ove FAZE 8.