"""Spike: OpenAI Realtime glas preko WebSocket-a, bez browsera.

Odgovara na jedino pitanje koje može ubiti Electron→PySide6 migraciju:
može li glasovni pipeline raditi iz čistog Pythona (sounddevice + websockets)
umjesto iz browsera (WebRTC), sa prihvatljivom latencijom i bez eha?

Ovo NIJE produkcijski kod — namjerno je jedan fajl bez apstrakcija.
Mjeri: latenciju do prvog zvuka, sumnju na eho, prekide u audio streamu.
Vidi: docs/ELECTRON_MIGRATION_PLAN_REVISED_2026-07-19.md (razlog nastanka)
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path

try:
    import sounddevice as sd
    import websockets
    from websockets.asyncio.client import connect
except ImportError as exc:  # pragma: no cover - spike
    print(f"Nedostaje biblioteka: {exc}")
    print("Instaliraj:  pip install sounddevice websockets")
    sys.exit(1)


# ── Konfiguracija ────────────────────────────────────────────────────────────

MODEL = "gpt-realtime"  # isti model koji koristi electron/ipc_handlers/realtime.cjs
URL = f"wss://api.openai.com/v1/realtime?model={MODEL}"

SAMPLE_RATE = 24_000  # Realtime API traži PCM16 @ 24kHz mono
CHANNELS = 1
DTYPE = "int16"
BLOCK = 480  # 20ms po chunku — kompromis latencija/overhead

INSTRUKCIJE = (
    "Ti si Riki, glasovni asistent. Govoriš srpski, latinicom. "
    "Odgovaraj kratko — jedna do dvije rečenice. Ovo je test glasovnog puta. "
    "Imaš tri alata: koliko_je_sati (kad te pitaju za vrijeme), "
    "zapisi_belesku (kad te zamole da nešto zapamtiš ili zabilježiš), i "
    "obrisi_test_fajl (VISOK RIZIK — kad te zamole da obrišeš test fajl). "
    "Ako obrisi_test_fajl vrati da čeka potvrdu, kratko reci korisniku da "
    "čekaš njegovu potvrdu i ne pokušavaj sam ponovo. Kad ti kasnije kažem "
    "da je odobreno ili da probaš ponovo, pozovi isti alat opet."
)


# ── Alati (dokaz da glasovni tok može pozvati Python funkciju) ────────────────

# GA Realtime oblik: type/name/description/parameters (JSON schema) na vrhu.
DEFINICIJE_ALATA = [
    {
        "type": "function",
        "name": "koliko_je_sati",
        "description": "Vraća trenutno vrijeme i datum. Bez argumenata.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "type": "function",
        "name": "zapisi_belesku",
        "description": "Zapisuje kratku belešku u lokalni fajl.",
        "parameters": {
            "type": "object",
            "properties": {
                "tekst": {"type": "string", "description": "Sadržaj beleške"}
            },
            "required": ["tekst"],
        },
    },
    {
        "type": "function",
        "name": "obrisi_test_fajl",
        "description": (
            "VISOK RIZIK. Briše lokalni test fajl. Zahtijeva eksplicitnu "
            "potvrdu korisnika prije izvršenja — isti obrazac kao permission "
            "engine u pravoj aplikaciji (python_backend/app/agent/"
            "permission_engine.py)."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]

BELESKE_FAJL = Path(__file__).resolve().parent / "spike_beleske.txt"
TEST_FAJL_ZA_BRISANJE = Path(__file__).resolve().parent / "spike_test_za_brisanje.txt"

# Simulira permission_engine confirmation_id gate: prazan dok korisnik ne
# "odobri" (Enter u terminalu) — isto ponašanje kao GUI confirmation dialog.
ODOBRENJE = threading.Event()


def izvrsi_alat(ime: str, args: dict) -> dict:
    """Izvršava lokalni Python alat i vraća rezultat za agenta.

    Namjerno jednostavno: jedan čita (vrijeme), jedan ima efekat (upis u fajl)
    — dovoljno da dokaže da glasovni tool-calling radi kroz čist Python.
    """
    if ime == "koliko_je_sati":
        sada = time.strftime("%H:%M, %d.%m.%Y.")
        return {"ok": True, "vrijeme": sada}

    if ime == "zapisi_belesku":
        tekst = str(args.get("tekst", "")).strip()
        if not tekst:
            return {"ok": False, "greska": "prazan tekst"}
        with BELESKE_FAJL.open("a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M')}] {tekst}\n")
        return {"ok": True, "zapisano": tekst}

    if ime == "obrisi_test_fajl":
        # Isti oblik kao CONFIRMATION_REQUIRED u permission_engine.py —
        # alat se NE izvršava dok confirmation_id (ovdje: ODOBRENJE) ne postoji.
        if not ODOBRENJE.is_set():
            return {
                "ok": False,
                "waiting_confirmation": True,
                "message": "Potrebna je tvoja potvrda prije brisanja.",
            }
        if TEST_FAJL_ZA_BRISANJE.exists():
            TEST_FAJL_ZA_BRISANJE.unlink()
            return {"ok": True, "obrisano": True}
        return {"ok": True, "obrisano": False, "napomena": "fajl već ne postoji"}

    return {"ok": False, "greska": f"nepoznat alat: {ime}"}


# ── Stanje mjerenja ──────────────────────────────────────────────────────────


class Mjerenja:
    """Skuplja metrike tokom sesije i ispisuje izvještaj na kraju."""

    def __init__(self) -> None:
        self.latencije_ms: list[float] = []
        self.govor_stao_u: float | None = None
        self.ceka_prvi_audio = False
        self.zvuk_svira_do = 0.0
        self.sumnja_na_eho = 0
        self.okretaja = 0
        self.underrun = 0
        self.alati_pozvani: list[str] = []
        self.potvrda_trazena = False
        self.potvrda_zavrsena = False

    def alat_pozvan(self, ime: str) -> None:
        self.alati_pozvani.append(ime)

    def govor_zaustavljen(self) -> None:
        self.govor_stao_u = time.perf_counter()
        self.ceka_prvi_audio = True

    def prvi_audio_stigao(self) -> None:
        if self.ceka_prvi_audio and self.govor_stao_u is not None:
            ms = (time.perf_counter() - self.govor_stao_u) * 1000
            self.latencije_ms.append(ms)
            self.okretaja += 1
            print(f"  ⏱  odgovor za {ms:.0f} ms")
        self.ceka_prvi_audio = False

    def govor_poceo(self) -> None:
        # Ako VAD čuje "govor" dok zvučnik još svira, to je vjerovatno eho.
        if time.perf_counter() < self.zvuk_svira_do:
            self.sumnja_na_eho += 1
            print("  ⚠  VAD reagovao dok agent govori → moguć EHO")

    def izvjestaj(self) -> None:
        print("\n" + "═" * 58)
        print("  REZULTAT SPIKE-a")
        print("═" * 58)

        if not self.latencije_ms:
            print("\n  Nije zabilježen nijedan odgovor.")
            print("  Provjeri mikrofon i da li te je uopšte čuo.")
            return

        prosjek = sum(self.latencije_ms) / len(self.latencije_ms)
        najbrzi = min(self.latencije_ms)
        najsporiji = max(self.latencije_ms)

        print(f"\n  Razmjena (govor → odgovor):  {self.okretaja}")
        print(f"  Latencija do prvog zvuka:")
        print(f"      prosjek    {prosjek:7.0f} ms")
        print(f"      najbrži    {najbrzi:7.0f} ms")
        print(f"      najsporiji {najsporiji:7.0f} ms")

        if prosjek < 800:
            ocjena = "ODLIČNO — neprimjetno u razgovoru"
        elif prosjek < 1200:
            ocjena = "DOBRO — primjetno ali prirodno"
        elif prosjek < 2000:
            ocjena = "GRANIČNO — osjeti se pauza"
        else:
            ocjena = "LOŠE — razgovor djeluje trom"
        print(f"      → {ocjena}")

        print(f"\n  Sumnja na eho:  {self.sumnja_na_eho}")
        if self.sumnja_na_eho == 0:
            print("      → čisto (ili si koristio slušalice)")
        elif self.sumnja_na_eho <= 2:
            print("      → povremeno; provjeri bez slušalica")
        else:
            print("      → ČEST EHO: bez slušalica treba AEC biblioteka")

        print(f"\n  Alati pozvani:  {len(self.alati_pozvani)}")
        if self.alati_pozvani:
            for ime in self.alati_pozvani:
                print(f"      • {ime}")
            print("      → glasovni tool-calling RADI")
        else:
            print("      → nijedan alat nije pozvan (pitaj 'koliko je sati')")

        if self.underrun:
            print(f"\n  Prekidi u zvuku: {self.underrun} (isprekidan zvuk)")

        print(f"\n  Confirmation flow (visok rizik):")
        if not self.potvrda_trazena:
            print("      → nije testiran (probaj 'obriši test fajl')")
        elif self.potvrda_zavrsena:
            print("      → TRAŽENO → ODOBRENO → IZVRŠENO, sve preko glasa")
        else:
            print("      → traženo, ali nije završeno (ENTER nije pritisnut?)")

        print("\n" + "─" * 58)
        print("  ODLUKA")
        print("─" * 58)
        glas_ok = prosjek < 1200 and self.sumnja_na_eho <= 2
        alati_ok = len(self.alati_pozvani) > 0
        potvrda_ok = not self.potvrda_trazena or self.potvrda_zavrsena

        if glas_ok and alati_ok and self.potvrda_zavrsena:
            print("  ✓ Glas, tool-calling I confirmation flow rade.")
            print("    Glasovna strana migracije je POTPUNO zelena.")
        elif glas_ok and alati_ok and not potvrda_ok:
            print("  ~ Glas i obični alati rade, ali confirmation flow nije")
            print("    dovršen ovaj put (probaj ponovo, pritisni ENTER kad")
            print("    agent kaže da čeka potvrdu).")
        elif glas_ok and not alati_ok:
            print("  ✓ Glas radi, ali alati nisu testirani ovaj put.")
            print("    Pokreni ponovo i pitaj 'koliko je sati'.")
        elif prosjek < 2000:
            print("  ~ Radi, ali sporije od WebRTC-a.")
            print("    Pitanje je da li ti je ta razlika prihvatljiva.")
        else:
            print("  ✗ Prespor za prirodan razgovor.")
            print("    Provjeri mrežu; ako se ponovi — Electron/WebRTC ostaje.")
        print()


# ── Učitavanje ključa ────────────────────────────────────────────────────────


def ucitaj_kljuc() -> str:
    """Čita OPENAI_API_KEY iz okruženja ili .env.local (ne ispisuje ga)."""
    kljuc = os.environ.get("OPENAI_API_KEY")
    if kljuc:
        return kljuc

    env = Path(__file__).resolve().parent.parent / ".env.local"
    if env.exists():
        for linija in env.read_text(encoding="utf-8").splitlines():
            linija = linija.strip()
            if linija.startswith("OPENAI_API_KEY="):
                return linija.split("=", 1)[1].strip().strip("\"'")

    print("Nema OPENAI_API_KEY — ni u okruženju ni u .env.local")
    sys.exit(1)


# ── Glavna petlja ────────────────────────────────────────────────────────────


# Globalno da bi izvještaj preživio Ctrl+C prekid glavne petlje.
MJERENJA = Mjerenja()


def cekaj_odobrenje_u_terminalu() -> None:
    """Blokira dok korisnik ne pritisne Enter — simulira klik na 'Odobri'
    dugme u pravom confirmation dijalogu. Radi u zasebnoj niti jer input()
    blokira, a to ne smije stati asyncio petlju."""
    input()
    ODOBRENJE.set()


async def main() -> None:
    kljuc = ucitaj_kljuc()
    m = MJERENJA

    # Test fajl mora postojati da bi brisanje imalo šta da pokaže.
    if not TEST_FAJL_ZA_BRISANJE.exists():
        TEST_FAJL_ZA_BRISANJE.write_text("ovo je test fajl za spike\n", encoding="utf-8")

    threading.Thread(target=cekaj_odobrenje_u_terminalu, daemon=True).start()

    # Queue-ovi su thread-safe jer sounddevice callback radi u audio threadu,
    # a ne u asyncio petlji — asyncio.Queue bi ovdje bio pogrešan.
    mikrofon_q: queue.Queue[bytes] = queue.Queue()
    zvucnik_q: queue.Queue[bytes] = queue.Queue()

    # Leftover buffer: delta chunkovi iz OpenAI su veći od jednog audio bloka,
    # pa se višak MORA sačuvati za sljedeći callback — inače puca zvuk.
    ostatak = bytearray()

    def mikrofon_callback(indata, frames, time_info, status) -> None:
        if status:
            m.underrun += 1
        # RawInputStream daje sirov buffer; bytes() ga kopira iz audio threada.
        mikrofon_q.put(bytes(indata))

    def zvucnik_callback(outdata, frames, time_info, status) -> None:
        potrebno = frames * CHANNELS * 2  # 2 bajta po uzorku (int16 mono)
        # Dopuni ostatak iz queue-a dok ne skupimo dovoljno za ovaj blok.
        while len(ostatak) < potrebno:
            try:
                ostatak.extend(zvucnik_q.get_nowait())
            except queue.Empty:
                break

        if len(ostatak) >= potrebno:
            outdata[:] = bytes(ostatak[:potrebno])
            del ostatak[:potrebno]  # višak čuvamo za sljedeći callback
            # Agent trenutno govori — koristi se za detekciju eha.
            m.zvuk_svira_do = time.perf_counter() + 0.25
        else:
            # Nedovoljno audija — sviraj šta ima, ostatak tišina (ne pucaj).
            n = len(ostatak)
            outdata[:n] = bytes(ostatak)
            outdata[n:] = b"\x00" * (potrebno - n)
            del ostatak[:]

    print("─" * 58)
    print("  SPIKE: glas iz Pythona (bez browsera)")
    print("─" * 58)
    print(f"  Model:     {MODEL}")
    print(f"  Audio:     PCM16 {SAMPLE_RATE} Hz mono, {BLOCK} frames/chunk")
    print(f"  Mikrofon:  {sd.query_devices(kind='input')['name']}")
    print(f"  Zvučnik:   {sd.query_devices(kind='output')['name']}")
    print("─" * 58)

    # GA oblik: nema više "OpenAI-Beta: realtime=v1" — beta oblik je ugašen
    # (server vraća 4000 beta_api_shape_disabled ako se pošalje stari oblik).
    async with connect(
        URL,
        additional_headers={"Authorization": f"Bearer {kljuc}"},
        max_size=None,
    ) as ws:
        # Server prvo šalje session.created; tek onda ima smisla slati update.
        while True:
            prvi = json.loads(await ws.recv())
            if prvi.get("type") == "session.created":
                break
            if prvi.get("type") == "error":
                print(f"  ✗ {prvi.get('error', {}).get('message')}")
                return

        # Isti oblik koji koristi electron/ipc_handlers/realtime.cjs (GA):
        # type/output_modalities na vrhu, audio ugniježđen sa format objektima.
        await ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "type": "realtime",
                        "model": MODEL,
                        "output_modalities": ["audio"],
                        "instructions": INSTRUKCIJE,
                        "tool_choice": "auto",
                        "tools": DEFINICIJE_ALATA,
                        "audio": {
                            "input": {
                                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                                # near_field = mikrofon blizu usta (slušalice).
                                # Za laptop mikrofon probaj "far_field".
                                "noise_reduction": {"type": "near_field"},
                                "turn_detection": {
                                    "type": "semantic_vad",
                                    "eagerness": "medium",
                                    "create_response": True,
                                    "interrupt_response": True,
                                },
                                "transcription": {
                                    "model": "whisper-1",
                                    "language": "sr",
                                },
                            },
                            "output": {
                                "format": {"type": "audio/pcm", "rate": SAMPLE_RATE},
                                "voice": "cedar",
                            },
                        },
                    },
                }
            )
        )

        async def salji() -> None:
            """Šalje mikrofon u WebSocket, chunk po chunk."""
            while True:
                try:
                    chunk = mikrofon_q.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.005)
                    continue
                await ws.send(
                    json.dumps(
                        {
                            "type": "input_audio_buffer.append",
                            "audio": base64.b64encode(chunk).decode(),
                        }
                    )
                )

        # GA je preimenovao dio događaja (response.audio.* → response.output_audio.*).
        # Hvatamo oba oblika da spike ne pukne na razlici u imenu.
        AUDIO_DELTA = {"response.audio.delta", "response.output_audio.delta"}
        TRANSKRIPT_GOTOV = {
            "response.audio_transcript.done",
            "response.output_audio_transcript.done",
        }
        POZNATI_TIHI = {
            "session.updated",
            "response.created",
            "response.output_item.added",
            "response.output_item.done",
            "response.content_part.added",
            "response.content_part.done",
            "conversation.item.created",
            "conversation.item.added",
            "conversation.item.done",
            "rate_limits.updated",
            "input_audio_buffer.committed",
            "output_audio_buffer.started",
            "output_audio_buffer.stopped",
            "response.audio.done",
            "response.output_audio.done",
            "response.audio_transcript.delta",
            "response.output_audio_transcript.delta",
        }
        vidjeni_nepoznati: set[str] = set()

        async def primaj() -> None:
            """Obrađuje događaje sa servera i puni zvučnik."""
            async for poruka in ws:
                dog = json.loads(poruka)
                tip = dog.get("type", "")

                if tip in AUDIO_DELTA:
                    m.prvi_audio_stigao()
                    zvucnik_q.put(base64.b64decode(dog["delta"]))

                elif tip == "input_audio_buffer.speech_started":
                    m.govor_poceo()
                    print("\n  🎤 slušam…")

                elif tip == "input_audio_buffer.speech_stopped":
                    m.govor_zaustavljen()

                elif tip in TRANSKRIPT_GOTOV:
                    print(f"  🔊 Riki: {dog.get('transcript', '').strip()}")

                elif tip == "conversation.item.input_audio_transcription.completed":
                    print(f"  💬 ti: {dog.get('transcript', '').strip()}")

                elif tip == "response.done":
                    # Agent je možda zatražio alat — hvata se iz output niza,
                    # isti obrazac koji koristi src/lib/realtime.ts (red 742).
                    izlazi = dog.get("response", {}).get("output", [])
                    for item in izlazi:
                        if item.get("type") != "function_call":
                            continue
                        ime = item.get("name", "")
                        call_id = item.get("call_id", "")
                        try:
                            args = json.loads(item.get("arguments") or "{}")
                        except json.JSONDecodeError:
                            args = {}
                        print(f"  🔧 alat: {ime}({json.dumps(args, ensure_ascii=False)})")
                        m.alat_pozvan(ime)

                        rezultat = izvrsi_alat(ime, args)
                        if rezultat.get("waiting_confirmation"):
                            m.potvrda_trazena = True
                            print("     ⏸  ČEKA POTVRDU — pritisni ENTER u terminalu da odobriš")
                        elif ime == "obrisi_test_fajl" and rezultat.get("ok"):
                            m.potvrda_zavrsena = True
                        print(f"     → {json.dumps(rezultat, ensure_ascii=False)}")

                        # Vrati rezultat agentu, pa traži da nastavi (izgovori ga).
                        await ws.send(
                            json.dumps(
                                {
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": call_id,
                                        "output": json.dumps(rezultat, ensure_ascii=False),
                                    },
                                }
                            )
                        )
                        await ws.send(json.dumps({"type": "response.create"}))

                elif tip == "error":
                    greska = dog.get("error", {})
                    print(f"\n  ✗ GREŠKA: {greska.get('message')}")
                    if greska.get("code"):
                        print(f"    kod: {greska.get('code')}")

                elif tip not in POZNATI_TIHI and tip not in vidjeni_nepoznati:
                    # Ne pogađamo imena događaja — prijavi ono što ne prepoznajemo.
                    vidjeni_nepoznati.add(tip)
                    print(f"  · (nepoznat događaj: {tip})")

        async def prati_odobrenje() -> None:
            """Kad korisnik pritisne Enter, automatski nudguje model da ponovi
            akciju — isti obrazac kao 'Confirmation Bridge' u pravoj aplikaciji
            (src/lib/realtime.ts:614): nakon odobrenja se AUTOMATSKI nastavlja
            originalna radnja, korisnik ne mora ponovo tražiti glasom."""
            while True:
                await asyncio.sleep(0.2)
                if ODOBRENJE.is_set() and m.potvrda_trazena and not m.potvrda_zavrsena:
                    print("\n  ✅ Odobreno u terminalu — automatski nastavljam radnju…")
                    await ws.send(
                        json.dumps(
                            {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "message",
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "input_text",
                                            "text": (
                                                "[Potvrda odobrena u dijalogu] "
                                                "Izvrši sada radnju koju si čekao."
                                            ),
                                        }
                                    ],
                                },
                            }
                        )
                    )
                    await ws.send(json.dumps({"type": "response.create"}))
                    return  # jedan test ciklus je dovoljan za spike

        # RawInputStream/RawOutputStream rade sa sirovim bajtovima umjesto
        # numpy array-a — nema (frames, channels) shape zamke, čist PCM prolaz.
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK,
            callback=mikrofon_callback,
        ), sd.RawOutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK,
            callback=zvucnik_callback,
        ):
            print("\n  Spreman. Govori normalno.")
            print("  Testiraj: 'koliko je sati', 'zapiši belešku da...',")
            print("            'obriši test fajl' (visok rizik → traži ENTER)")
            print("  Prekid: Ctrl+C\n")
            await asyncio.gather(salji(), primaj(), prati_odobrenje())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # očekivan način izlaza — izvještaj slijedi
    except websockets.exceptions.InvalidStatus as exc:
        print(f"\n  ✗ Server odbio konekciju: {exc}")
        print("    Provjeri API ključ i pristup Realtime API-ju.")
    except Exception as exc:  # pragma: no cover - spike
        print(f"\n  ✗ {type(exc).__name__}: {exc}")
    finally:
        MJERENJA.izvjestaj()
