# Ricky — Assets / Branding Folder Reminder

## Svrha

Ovaj dokument je podsjetnik za izdvajanje i organizaciju svih ikonica i brending elemenata koji će se koristiti u Ricky aplikaciji.

Cilj je da agent tokom rada ne izmišlja ikonice i vizuelne elemente, nego da ih uzima iz unaprijed pripremljenog foldera.

Planirana putanja u projektu:

```txt
C:\Users\38765\Desktop\Nas-agent\assets\brending
```

---

# 1. Glavni brending asseti

Ovo su najvažniji vizuelni elementi Ricky aplikacije.

```txt
ricky-orb-main.png
ricky-orb-main.webp
ricky-orb-mini.png
ricky-orb-mini.webp
ricky-orb-idle.png
ricky-orb-listening.png
ricky-orb-speaking.png
ricky-orb-thinking.png
ricky-orb-warning.png
ricky-orb-error.png
ricky-logo-r.svg
ricky-logo-r.png
ricky-app-icon.ico
ricky-app-icon.png
```

## Objašnjenje

### `ricky-orb-main`

Veliki Ricky orb za glavni / idle ekran aplikacije.

Koristi se kada je Ricky u glavnom prozoru i predstavlja centralni vizuelni identitet asistenta.

### `ricky-orb-mini`

Mala verzija orb-a za minimized / floating companion avatar.

Koristi se kada je aplikacija sakrivena ili minimizovana, a Ricky ostaje kao mali floating avatar na ekranu.

### `ricky-logo-r`

Samo stilizovano slovo `R`, bez kruga.

Koristi se za manje UI lokacije, header, app icon varijante ili kao dio orb komponente.

### `ricky-app-icon`

Windows ikonica aplikacije za:

```txt
- taskbar
- installer
- title bar
- Start menu
- shortcut
```

---

# 2. Sidebar ikonice

Za lijevi navigacioni meni:

```txt
icon-home.svg
icon-activity.svg
icon-plans.svg
icon-memory.svg
icon-screenshots.svg
icon-settings.svg
```

## Namjena

```txt
Početna        -> icon-home.svg
Aktivnost      -> icon-activity.svg
Planovi        -> icon-plans.svg
Memorija       -> icon-memory.svg
Snimci ekrana  -> icon-screenshots.svg
Postavke       -> icon-settings.svg
```

---

# 3. Voice / audio ikonice

Za glasovne funkcije i voice-first UI:

```txt
icon-microphone.svg
icon-microphone-muted.svg
icon-audio-wave.svg
icon-listening.svg
icon-speaking.svg
icon-stop.svg
icon-pause.svg
icon-send.svg
```

## Namjena

```txt
icon-microphone.svg        -> glavni mikrofon
icon-microphone-muted.svg  -> mute/unmute
icon-audio-wave.svg        -> audio/voice indikator
icon-listening.svg         -> stanje slušanja
icon-speaking.svg          -> stanje govora
icon-stop.svg              -> stop listening / prekid
icon-pause.svg             -> pauza
icon-send.svg              -> pošalji tekst/komandu
```

---

# 4. Status ikonice

Za Activity, Plans, Confirmation i sistemska stanja:

```txt
icon-status-ready.svg
icon-status-running.svg
icon-status-success.svg
icon-status-warning.svg
icon-status-error.svg
icon-status-blocked.svg
icon-status-info.svg
```

## Preporuka

Ako je moguće, ove SVG ikonice treba da koriste:

```txt
currentColor
```

Tako se boja može kontrolisati kroz CSS, umjesto da bude trajno upisana u SVG.

---

# 5. Confirmation / safety ikonice

Za potvrde, rizike i sigurnosne akcije:

```txt
icon-warning.svg
icon-shield.svg
icon-lock.svg
icon-unlock.svg
icon-risk-low.svg
icon-risk-medium.svg
icon-risk-high.svg
icon-risk-critical.svg
icon-confirm.svg
icon-cancel.svg
```

## Posebno važno

```txt
icon-warning.svg
```

Koristi se samo za:

```txt
- pažnju
- potvrdu
- rizik
- sigurnosno upozorenje
```

Ne koristiti warning ikonicu za običan progress ili normalne aktivnosti.

---

# 6. Tool / action ikonice

Za brze komande i lokalne alate:

```txt
icon-screenshot.svg
icon-open-app.svg
icon-open-url.svg
icon-clipboard.svg
icon-copy.svg
icon-save.svg
icon-edit.svg
icon-email.svg
icon-calendar.svg
icon-document.svg
icon-dictation.svg
```

## Namjena

```txt
icon-screenshot.svg   -> screenshot
icon-open-app.svg     -> otvori aplikaciju
icon-open-url.svg     -> otvori URL
icon-clipboard.svg    -> clipboard akcije
icon-copy.svg         -> kopiraj
icon-save.svg         -> sačuvaj nacrt/fajl
icon-edit.svg         -> izmijeni tekst
icon-email.svg        -> email/draft/slanje
icon-calendar.svg     -> planiranje/sastanak
icon-document.svg     -> dokument
icon-dictation.svg    -> diktirani tekst
```

---

# 7. Window / app control ikonice

Za Electron top bar i kontrole prozora:

```txt
icon-minimize.svg
icon-maximize.svg
icon-restore.svg
icon-close.svg
icon-fullscreen.svg
icon-exit-fullscreen.svg
```

## Namjena

```txt
icon-minimize.svg         -> minimizuj
icon-maximize.svg         -> maksimizuj
icon-restore.svg          -> vrati prozor
icon-close.svg            -> zatvori
icon-fullscreen.svg       -> fullscreen
icon-exit-fullscreen.svg  -> izađi iz fullscreen-a
```

---

# 8. Drawer / navigation ikonice

Za dropdown menije, drawer-e i male UI kontrole:

```txt
icon-chevron-down.svg
icon-chevron-right.svg
icon-arrow-right.svg
icon-arrow-left.svg
icon-more.svg
icon-filter.svg
icon-search.svg
icon-close-small.svg
```

## Namjena

```txt
icon-chevron-down.svg   -> dropdown
icon-chevron-right.svg  -> nested item / ulazak
icon-arrow-right.svg    -> idi dalje
icon-arrow-left.svg     -> nazad
icon-more.svg           -> više opcija
icon-filter.svg         -> filter
icon-search.svg         -> pretraga
icon-close-small.svg    -> zatvori panel/modal
```

---

# 9. Model / AI / backend ikonice

Za buduće Settings, Model Manager i sistemski status:

```txt
icon-model.svg
icon-cloud.svg
icon-local.svg
icon-database.svg
icon-backend.svg
icon-api.svg
icon-realtime.svg
```

## Namjena

```txt
icon-model.svg     -> model manager / AI model
icon-cloud.svg     -> cloud / OpenAI
icon-local.svg     -> lokalni režim
icon-database.svg  -> SQLite / storage
icon-backend.svg   -> Python backend
icon-api.svg       -> API konekcije
icon-realtime.svg  -> OpenAI Realtime voice model
```

---

# 10. Predložena struktura foldera

Preporučena organizacija unutar:

```txt
assets/brending
```

Struktura:

```txt
assets/
  brending/
    logo/
      ricky-logo-r.svg
      ricky-logo-r.png
      ricky-app-icon.ico
      ricky-app-icon.png

    orb/
      ricky-orb-main.png
      ricky-orb-main.webp
      ricky-orb-mini.png
      ricky-orb-mini.webp
      ricky-orb-idle.png
      ricky-orb-listening.png
      ricky-orb-speaking.png
      ricky-orb-thinking.png
      ricky-orb-warning.png
      ricky-orb-error.png

    icons/
      navigation/
        icon-home.svg
        icon-activity.svg
        icon-plans.svg
        icon-memory.svg
        icon-screenshots.svg
        icon-settings.svg

      voice/
        icon-microphone.svg
        icon-microphone-muted.svg
        icon-audio-wave.svg
        icon-listening.svg
        icon-speaking.svg
        icon-stop.svg
        icon-pause.svg
        icon-send.svg

      status/
        icon-status-ready.svg
        icon-status-running.svg
        icon-status-success.svg
        icon-status-warning.svg
        icon-status-error.svg
        icon-status-blocked.svg
        icon-status-info.svg

      safety/
        icon-warning.svg
        icon-shield.svg
        icon-lock.svg
        icon-unlock.svg
        icon-risk-low.svg
        icon-risk-medium.svg
        icon-risk-high.svg
        icon-risk-critical.svg
        icon-confirm.svg
        icon-cancel.svg

      actions/
        icon-screenshot.svg
        icon-open-app.svg
        icon-open-url.svg
        icon-clipboard.svg
        icon-copy.svg
        icon-save.svg
        icon-edit.svg
        icon-email.svg
        icon-calendar.svg
        icon-document.svg
        icon-dictation.svg

      window/
        icon-minimize.svg
        icon-maximize.svg
        icon-restore.svg
        icon-close.svg
        icon-fullscreen.svg
        icon-exit-fullscreen.svg

      ui/
        icon-chevron-down.svg
        icon-chevron-right.svg
        icon-arrow-right.svg
        icon-arrow-left.svg
        icon-more.svg
        icon-filter.svg
        icon-search.svg
        icon-close-small.svg

      system/
        icon-model.svg
        icon-cloud.svg
        icon-local.svg
        icon-database.svg
        icon-backend.svg
        icon-api.svg
        icon-realtime.svg
```

---

# 11. Pravilo za formate

## Obične ikonice

Koristiti:

```txt
SVG
```

Razlog:

```txt
- skalabilne su
- lake su za promjenu boje kroz CSS
- idealne su za UI ikonice
- ne gube kvalitet na različitim rezolucijama
```

## Ricky orb

Koristiti:

```txt
PNG
WEBP
```

Razlog:

```txt
- orb ima glow, teksture i kompleksnije vizuelne efekte
- lakše ga je koristiti kao sliku
- WEBP može smanjiti veličinu fajla
```

## Windows aplikacija

Koristiti:

```txt
ICO
PNG
```

Razlog:

```txt
- .ico je potreban za Windows app icon / installer / shortcut
- .png je koristan za UI i preview
```

## Animirani orb kasnije

Moguće opcije:

```txt
CSS animation
SVG animation
Lottie
WebM
Canvas
```

Preporuka:

```txt
Prvo static state slike, pa kasnije animacija kroz CSS/SVG/Canvas.
```

Ne praviti odmah komplikovane video animacije ako nije potrebno.

---

# 12. Najvažniji asseti za prvu rundu

Prvo pripremiti samo najbitnije:

```txt
ricky-logo-r.svg
ricky-orb-main.png
ricky-orb-mini.png
ricky-app-icon.ico

icon-home.svg
icon-activity.svg
icon-plans.svg
icon-memory.svg
icon-screenshots.svg
icon-settings.svg

icon-microphone.svg
icon-send.svg
icon-warning.svg
icon-status-success.svg
icon-close.svg
icon-more.svg
```

Ovo je dovoljno da agent može odmah da popravi glavni UI bez lutanja.

---

# 13. Pravila za agenta

Agent tokom implementacije mora:

```txt
1. Uzimati ikonice iz assets/brending foldera.
2. Ne izmišljati nove ikonice ako asset već postoji.
3. Ne koristiti emoji kao zamjenu za UI ikonice.
4. Ne koristiti random icon library ako je dogovoreni asset pripremljen.
5. Poštovati naziv fajlova.
6. Ako asset nedostaje, prvo prijaviti koji asset nedostaje.
7. Ricky orb koristiti kao glavni identitet, ne kao dekoraciju.
8. Mini orb koristiti za minimized/floating companion mode.
9. Warning ikone koristiti samo za rizik/potvrdu.
10. Backend/debug evente ne prikazivati kao brending ili korisničke aktivnosti.
```

---

# 14. Napomena za trenutni UI refaktor

U trenutnom UI refaktoru obavezno zamijeniti:

```txt
stari plain R circle avatar
```

sa:

```txt
ricky-orb-main.png
```

Za minimized / floating mode koristiti:

```txt
ricky-orb-mini.png
```

Za header / malu ikonicu koristiti:

```txt
ricky-logo-r.svg
```

ili smanjenu verziju:

```txt
ricky-app-icon.png
```

---

# 15. Finalna svrha ovog foldera

`assets/brending` treba da postane jedno mjesto iz kojeg agent uzima sve vizuelne identitetske elemente Ricky aplikacije.

To sprječava:

```txt
- lutanje u dizajnu
- nasumične ikonice
- nedosljedan stil
- promjene vizuelnog identiteta iz taska u task
- generisanje novih simbola bez kontrole
```

Glavna ideja:

```txt
Jedan folder.
Jedan stil.
Jedan Ricky identitet.
Agent samo koristi pripremljene assete.
```
