# Ricky Orb Animation Plan

## Svrha

Ovaj dokument opisuje kako implementirati animaciju Ricky orb-a u aplikaciji.

Cilj animacije nije da bude komplikovana, nego da Ricky djeluje živ, profesionalan i jasno povezan sa stanjem asistenta.

Animira se prvenstveno:

```txt
krug / voice ring oko stilizovanog R
```

a ne samo slovo `R`.

---

# 1. Osnovna odluka

Za prvu verziju koristiti:

```txt
PNG/WebP orb asset
+ CSS animirani ringovi
+ promjena animacije po VoiceState
```

Ne koristiti odmah:

```txt
- Lottie
- WebGL
- video animacije
- kompleksan canvas audio visualizer
```

Razlog:

```txt
- CSS animacija je jednostavna
- lako se kontroliše
- ne komplikuje build
- radi dobro u Electron/React UI-ju
- dovoljno je za premium MVP izgled
```

Kasnije se može dodati napredniji canvas/audio-reactive ring.

---

# 2. Asseti koje treba koristiti

Orb asseti se nalaze u:

```txt
C:\Users\38765\Desktop\Nas-agent\assets\brending\orb
```

Najvažniji fajlovi:

```txt
ricky-orb-main.png
ricky-orb-mini.png
ricky-orb-idle.png
ricky-orb-listening.png
ricky-orb-speaking.png
ricky-orb-thinking.png
ricky-orb-warning.png
ricky-orb-error.png
```

Preporuka:

```txt
Main UI:
assets/brending/orb/ricky-orb-main.png

Floating companion:
assets/brending/orb/ricky-orb-mini.png
```

State varijante koristiti samo ako želiš jače vizuelno razlikovanje stanja.

---

# 3. VoiceState mapiranje

Orb treba da reaguje na stanje asistenta.

Predloženi state model:

```ts
export type RickyOrbState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "warning"
  | "error"
  | "muted";
```

Mapiranje:

```txt
idle       -> Ricky je spreman, miran soft pulse
listening  -> korisnik govori, aktivniji ring
thinking   -> Ricky obrađuje, sporiji glow
speaking   -> Ricky govori, najjači voice pulse
warning    -> čeka potvrdu, blagi warning ring
error      -> greška, crveni kratki pulse
muted      -> utišan, sivi/muted izgled
```

---

# 4. Vizuelna pravila animacije

## 4.1 Idle

Idle mora biti miran.

```txt
- blago disanje
- spor pulse
- nizak intenzitet glow-a
- bez agresivnog kretanja
```

## 4.2 Listening

Listening mora pokazati da Ricky prima govor.

```txt
- outer ring pulsira brže
- ring se blago širi i skuplja
- cyan/blue glow jači nego u idle stanju
```

## 4.3 Thinking

Thinking nije audio state.

```txt
- sporiji glow
- blago kružno/orbit kretanje
- manje waveform energije
```

## 4.4 Speaking

Speaking je najživlja animacija.

```txt
- voice ring pulsira kao govor
- unutrašnji i spoljašnji ring rade različitim tempom
- glow je najjači, ali ne smije biti haotičan
```

Inspiracija:

```txt
Siri-like voice orb
```

ali ne kopirati Apple UI doslovno.

## 4.5 Warning

Warning ne smije praviti previše buke.

Ako postoji confirmation modal, modal je glavni fokus.

```txt
- orb može dobiti blagi orange ring
- animacija mirna
- ne pretjerivati
```

## 4.6 Error

Error mora biti jasan, ali kratak.

```txt
- crveni ring
- kratki pulse/shake
- ne animirati beskonačno agresivno
```

## 4.7 Muted

Muted znači da Ricky ne sluša.

```txt
- smanjena opacity
- grayscale / muted ring
- bez aktivnih pulse animacija
```

---

# 5. React komponenta

Kreirati komponentu:

```txt
src/components/assistant/RickyOrb.tsx
```

Primjer:

```tsx
import "./RickyOrb.css";

export type RickyOrbState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "warning"
  | "error"
  | "muted";

type RickyOrbProps = {
  state?: RickyOrbState;
  size?: "small" | "medium" | "large" | "floating";
  className?: string;
};

export function RickyOrb({
  state = "idle",
  size = "large",
  className = "",
}: RickyOrbProps) {
  return (
    <div className={`ricky-orb ricky-orb--${state} ricky-orb--${size} ${className}`}>
      <div className="ricky-orb__ring ricky-orb__ring--outer" />
      <div className="ricky-orb__ring ricky-orb__ring--middle" />
      <div className="ricky-orb__ring ricky-orb__ring--inner" />

      <img
        className="ricky-orb__image"
        src="/assets/brending/orb/ricky-orb-main.png"
        alt="Ricky"
        draggable={false}
      />
    </div>
  );
}
```

---

# 6. CSS animacija

Kreirati fajl:

```txt
src/components/assistant/RickyOrb.css
```

Primjer CSS-a:

```css
.ricky-orb {
  position: relative;
  display: grid;
  place-items: center;
  isolation: isolate;
  pointer-events: auto;
}

.ricky-orb--large {
  width: 280px;
  height: 280px;
}

.ricky-orb--medium {
  width: 180px;
  height: 180px;
}

.ricky-orb--small {
  width: 56px;
  height: 56px;
}

.ricky-orb--floating {
  width: 84px;
  height: 84px;
  opacity: 0.78;
  transition:
    opacity 180ms ease,
    transform 180ms ease,
    filter 180ms ease;
}

.ricky-orb--floating:hover {
  opacity: 1;
  transform: scale(1.04);
  filter: drop-shadow(0 0 18px rgba(62, 166, 255, 0.45));
}

.ricky-orb__image {
  position: relative;
  z-index: 4;
  width: 78%;
  height: 78%;
  object-fit: contain;
  user-select: none;
  filter:
    drop-shadow(0 0 16px rgba(62, 166, 255, 0.45))
    drop-shadow(0 0 36px rgba(62, 166, 255, 0.18));
}

.ricky-orb__ring {
  position: absolute;
  inset: 12%;
  border-radius: 999px;
  border: 1px solid rgba(91, 209, 255, 0.35);
  z-index: 1;
  pointer-events: none;
}

.ricky-orb__ring--outer {
  inset: 1%;
  border-color: rgba(62, 166, 255, 0.22);
  box-shadow:
    0 0 22px rgba(62, 166, 255, 0.22),
    inset 0 0 22px rgba(62, 166, 255, 0.1);
}

.ricky-orb__ring--middle {
  inset: 8%;
  border-color: rgba(157, 220, 255, 0.32);
  box-shadow:
    0 0 18px rgba(62, 166, 255, 0.22),
    inset 0 0 18px rgba(157, 220, 255, 0.1);
}

.ricky-orb__ring--inner {
  inset: 18%;
  border-color: rgba(126, 246, 255, 0.25);
  box-shadow:
    0 0 14px rgba(126, 246, 255, 0.24),
    inset 0 0 14px rgba(126, 246, 255, 0.1);
}
```

---

# 7. State animacije

## 7.1 Idle

```css
.ricky-orb--idle .ricky-orb__ring--outer {
  animation: ricky-idle-breathe 3.8s ease-in-out infinite;
}

.ricky-orb--idle .ricky-orb__ring--middle {
  animation: ricky-idle-breathe 4.4s ease-in-out infinite reverse;
}

.ricky-orb--idle .ricky-orb__image {
  animation: ricky-soft-float 5s ease-in-out infinite;
}
```

## 7.2 Listening

```css
.ricky-orb--listening .ricky-orb__ring--outer {
  animation: ricky-listening-pulse 1.25s ease-in-out infinite;
  border-color: rgba(91, 209, 255, 0.55);
}

.ricky-orb--listening .ricky-orb__ring--middle {
  animation: ricky-listening-pulse 0.95s ease-in-out infinite reverse;
  border-color: rgba(126, 246, 255, 0.45);
}

.ricky-orb--listening .ricky-orb__image {
  filter:
    drop-shadow(0 0 22px rgba(62, 166, 255, 0.65))
    drop-shadow(0 0 48px rgba(126, 246, 255, 0.2));
}
```

## 7.3 Thinking

```css
.ricky-orb--thinking .ricky-orb__ring--outer {
  animation: ricky-thinking-orbit 3.2s ease-in-out infinite;
  border-color: rgba(116, 104, 255, 0.35);
}

.ricky-orb--thinking .ricky-orb__ring--middle {
  animation: ricky-thinking-pulse 2.4s ease-in-out infinite;
  border-color: rgba(62, 166, 255, 0.28);
}
```

## 7.4 Speaking

```css
.ricky-orb--speaking .ricky-orb__ring--outer {
  animation: ricky-speaking-wave 0.9s ease-in-out infinite;
  border-color: rgba(91, 209, 255, 0.65);
}

.ricky-orb--speaking .ricky-orb__ring--middle {
  animation: ricky-speaking-wave 0.72s ease-in-out infinite reverse;
  border-color: rgba(159, 122, 255, 0.5);
}

.ricky-orb--speaking .ricky-orb__ring--inner {
  animation: ricky-speaking-inner 0.55s ease-in-out infinite;
  border-color: rgba(126, 246, 255, 0.5);
}

.ricky-orb--speaking .ricky-orb__image {
  animation: ricky-speaking-image 0.9s ease-in-out infinite;
}
```

## 7.5 Warning

```css
.ricky-orb--warning .ricky-orb__ring--outer {
  border-color: rgba(245, 165, 36, 0.55);
  box-shadow:
    0 0 20px rgba(245, 165, 36, 0.22),
    inset 0 0 20px rgba(245, 165, 36, 0.1);
  animation: ricky-warning-pulse 1.8s ease-in-out infinite;
}
```

## 7.6 Error

```css
.ricky-orb--error .ricky-orb__ring--outer {
  border-color: rgba(239, 68, 68, 0.65);
  box-shadow:
    0 0 22px rgba(239, 68, 68, 0.25),
    inset 0 0 22px rgba(239, 68, 68, 0.1);
  animation: ricky-error-pulse 0.55s ease-in-out 3;
}
```

## 7.7 Muted

```css
.ricky-orb--muted {
  opacity: 0.52;
  filter: grayscale(0.45);
}

.ricky-orb--muted .ricky-orb__ring {
  animation: none;
  border-color: rgba(141, 154, 170, 0.22);
  box-shadow: none;
}
```

---

# 8. Keyframes

```css
@keyframes ricky-idle-breathe {
  0%, 100% {
    transform: scale(1);
    opacity: 0.55;
  }
  50% {
    transform: scale(1.035);
    opacity: 0.85;
  }
}

@keyframes ricky-soft-float {
  0%, 100% {
    transform: translateY(0) scale(1);
  }
  50% {
    transform: translateY(-2px) scale(1.01);
  }
}

@keyframes ricky-listening-pulse {
  0%, 100% {
    transform: scale(0.98);
    opacity: 0.55;
  }
  50% {
    transform: scale(1.08);
    opacity: 1;
  }
}

@keyframes ricky-thinking-orbit {
  0%, 100% {
    transform: rotate(0deg) scale(1);
    opacity: 0.48;
  }
  50% {
    transform: rotate(6deg) scale(1.045);
    opacity: 0.82;
  }
}

@keyframes ricky-thinking-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.45;
  }
  50% {
    transform: scale(1.06);
    opacity: 0.72;
  }
}

@keyframes ricky-speaking-wave {
  0%, 100% {
    transform: scale(0.96);
    opacity: 0.48;
  }
  35% {
    transform: scale(1.1);
    opacity: 0.95;
  }
  65% {
    transform: scale(1.03);
    opacity: 0.72;
  }
}

@keyframes ricky-speaking-inner {
  0%, 100% {
    transform: scale(1);
    opacity: 0.45;
  }
  50% {
    transform: scale(1.12);
    opacity: 0.9;
  }
}

@keyframes ricky-speaking-image {
  0%, 100% {
    transform: scale(1);
    filter:
      drop-shadow(0 0 18px rgba(62, 166, 255, 0.55))
      drop-shadow(0 0 40px rgba(126, 246, 255, 0.2));
  }
  50% {
    transform: scale(1.025);
    filter:
      drop-shadow(0 0 26px rgba(62, 166, 255, 0.8))
      drop-shadow(0 0 58px rgba(126, 246, 255, 0.28));
  }
}

@keyframes ricky-warning-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.58;
  }
  50% {
    transform: scale(1.04);
    opacity: 0.9;
  }
}

@keyframes ricky-error-pulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.045);
  }
}
```

---

# 9. Accessibility / reduced motion

Obavezno dodati:

```css
@media (prefers-reduced-motion: reduce) {
  .ricky-orb,
  .ricky-orb *,
  .ricky-orb::before,
  .ricky-orb::after {
    animation: none !important;
    transition: none !important;
  }
}
```

Razlog:

```txt
Neki korisnici ne podnose konstantne animacije.
Aplikacija mora poštovati OS accessibility preference.
```

---

# 10. Floating companion orb

Za minimized/floating Ricky koristi istu komponentu sa `size="floating"`.

Kreirati:

```txt
src/companion/CompanionOrb.tsx
src/companion/CompanionOrb.css
```

Primjer:

```tsx
import { RickyOrb, RickyOrbState } from "../components/assistant/RickyOrb";
import "./CompanionOrb.css";

type CompanionOrbProps = {
  state: RickyOrbState;
  onOpenMainWindow: () => void;
};

export function CompanionOrb({ state, onOpenMainWindow }: CompanionOrbProps) {
  return (
    <button
      className="companion-orb"
      onClick={onOpenMainWindow}
      aria-label="Open Ricky"
    >
      <RickyOrb state={state} size="floating" />
    </button>
  );
}
```

CSS:

```css
.companion-orb {
  width: 96px;
  height: 96px;
  padding: 0;
  border: 0;
  background: transparent;
  display: grid;
  place-items: center;
  cursor: pointer;
  -webkit-app-region: drag;
}

.companion-orb:hover {
  -webkit-app-region: no-drag;
}

.companion-orb:focus-visible {
  outline: 2px solid rgba(62, 166, 255, 0.8);
  outline-offset: 4px;
  border-radius: 999px;
}
```

---

# 11. Companion opacity pravila

Floating orb ne smije biti previše agresivan.

Preporuka:

```txt
idle:
- opacity 0.70–0.80
- soft glow

hover:
- opacity 1.0
- malo jači glow

listening/speaking:
- opacity 0.95–1.0
- aktivan pulse

inactive:
- opacity 0.55–0.65
- mirniji glow
```

---

# 12. Povezivanje sa VoiceState

Orb komponenta ne treba sama da odlučuje state.

State dolazi iz aplikacije.

Primjer:

```tsx
const orbState = mapVoiceStateToOrbState(voiceState);

<RickyOrb state={orbState} size="large" />
```

Helper:

```ts
import type { RickyOrbState } from "../components/assistant/RickyOrb";

export function mapVoiceStateToOrbState(voiceState: string): RickyOrbState {
  switch (voiceState) {
    case "listening":
    case "transcribing":
      return "listening";

    case "thinking":
      return "thinking";

    case "speaking":
      return "speaking";

    case "waiting_confirmation":
      return "warning";

    case "error":
    case "backend_disconnected":
      return "error";

    case "muted":
      return "muted";

    case "idle":
    default:
      return "idle";
  }
}
```

---

# 13. Performance pravila

Animacija mora biti lagana.

Koristiti uglavnom:

```txt
transform
opacity
filter umjereno
```

Izbjegavati:

```txt
layout-changing properties
velike blur animacije na ogromnim elementima
previše paralelnih box-shadow animacija
```

Ako performanse padnu:

```txt
- smanjiti broj ringova sa 3 na 2
- smanjiti blur/shadow
- smanjiti frekvenciju animacije
- ugasiti inner ring animation
```

---

# 14. Šta agent NE SMIJE uraditi

```txt
1. Ne koristiti Lottie/WebGL/video u prvoj verziji.
2. Ne animirati 10 elemenata istovremeno.
3. Ne praviti kaotičan equalizer.
4. Ne koristiti warning/orange animaciju za normalne state-ove.
5. Ne mijenjati Ricky identitet u generički mikrofon.
6. Ne koristiti human avatar.
7. Ne stavljati tri nezavisne waveform animacije na ekran.
8. Ne ignorisati prefers-reduced-motion.
```

---

# 15. Acceptance criteria

Animacija je prihvatljiva kada:

```txt
- orb mirno diše u idle stanju
- listening jasno djeluje aktivnije od idle
- speaking izgleda kao voice pulse
- thinking je sporiji i manje audio-like
- warning ne preuzima fokus od confirmation modal-a
- error je vidljiv ali nije agresivan beskonačno
- floating orb je transparentniji i manje napadan
- animacija ne usporava UI
- reduced motion radi
```

---

# 16. Finalni zaključak

Prva verzija animacije treba biti:

```txt
jednostavna
CSS-based
state-driven
profesionalna
dovoljno živa
laka za održavanje
```

Ne treba sada praviti savršen audio-reactive engine.

Prvo implementirati:

```txt
RickyOrb.tsx
RickyOrb.css
mapVoiceStateToOrbState()
CompanionOrb.tsx
```

Tek kada GUI bude stabilan i liči na mockup, razmatrati napredniju Siri-like organsku animaciju kroz Canvas ili Lottie.
