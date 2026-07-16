# Browser Bridge — Produkcijska distribucija (C4)

## Pregled

Ricky Browser Bridge ekstenzija treba da bude distribuirana kroz zvanične
browser store-ove za svaki podržani Chromium browser. Ovo eliminiše potrebu
za ručnim `Load unpacked` postupkom za krajnje korisnike.

## Chrome Web Store (Chrome, Brave, Vivaldi, Opera, Opera GX, Chromium)

Većina Chromium browsera koristi Chrome Web Store za ekstenzije.

### Priprema

1. **ZIP arhiva**: Zapakovati `browser_extension/` folder:
   ```bash
   cd browser_extension && zip -r ../ricky-browser-bridge.zip . -x "*.git*"
   ```

2. **Store listing assets**:
   - Ikona 128x128 PNG (`icons/icon-128.png`)
   - Screenshot ekstenzije u akciji (1280x800 ili 640x400)
   - Promotional tile (440x280 ili 920x680 ili 1400x560)

3. **Manifest priprema**:
   - Verzija: semver (`1.0.0`)
   - Opis: jasno objašnjenje šta ekstenzija radi i šta NE radi
   - Privacy policy URL

### Proces objavljivanja

1. Otvoriti [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole)
2. Plaćanje jednokratne developer registracije (~$5)
3. Kreirati novi item → Upload ZIP arhive
4. Popuniti:
   - Description: "Lets the Ricky desktop companion safely list, activate, open, and close browser tabs. Never reads page content."
   - Category: Productivity
   - Language: English ( + srpski)
   - Privacy practices: obavezno navesti da ekstenzija ne čita sadržaj stranica
5. Submit for review (obično 1-3 dana)

### Privacy deklaracija

Obavezno navesti u Chrome Web Store listing-u:

```
Data collected: None
- This extension does NOT collect, store, or transmit any user data.
- It does NOT read page content, browsing history, cookies, or passwords.
- It only reads tab titles and URLs for the purpose of tab management,
  and only communicates with the locally installed Ricky desktop app
  via a secure localhost WebSocket (127.0.0.1).
- No data is sent to external servers, cloud services, or third parties.
```

## Microsoft Edge Add-ons

Edge ima sopstveni store, ali prihvata i Chrome Web Store ekstenzije.

### Opcija A: Edge Add-ons Store (preporučeno)

1. Otvoriti [Partner Center](https://partner.microsoft.com/en-us/dashboard/microsoftedge/overview)
2. Submit → New extension → Upload isti ZIP
3. Popuniti metadata (isti description kao za Chrome)

### Opcija B: Chrome Web Store (jednostavnije)

Edge korisnici mogu instalirati ekstenzije iz Chrome Web Store-a:
1. Otvoriti `edge://extensions`
2. Uključiti "Allow extensions from other stores"
3. Instalirati sa Chrome Web Store linka

## Brave / Vivaldi / Opera / Opera GX / Chromium

Svi ovi browseri koriste Chrome Web Store kao primarni izvor ekstenzija.
Nije potreban poseban listing za svaki — isti Chrome Web Store listing
pokriva sve. Korisnik instalira direktno iz Chrome Web Store-a u svom browseru.

## Settings integracija

### Development mode (default, `npm run dev`)
- Prikazuje `Load unpacked` instrukcije
- Lokalni pairing token flow

### Production mode
- Prikazuje "Install from Chrome Web Store" dugme/link
- Automatska detekcija browsera → odgovarajući store link
- Linkovi:
  - Chrome/Brave/Vivaldi/Opera/Chromium: `https://chrome.google.com/webstore/detail/[extension-id]`
  - Edge: `https://microsoftedge.microsoft.com/addons/detail/[extension-id]`

### Store linkovi

| Browser | Store URL |
|---------|-----------|
| Chrome | `https://chrome.google.com/webstore/detail/ricky-browser-bridge/[ID]` |
| Edge | `https://microsoftedge.microsoft.com/addons/detail/ricky-browser-bridge/[ID]` |
| Brave | Chrome Web Store (isti URL) |
| Vivaldi | Chrome Web Store (isti URL) |
| Opera | Chrome Web Store (isti URL) |
| Opera GX | Chrome Web Store (isti URL) |
| Chromium | Chrome Web Store (isti URL) |

## Extension ID

Development ID se mijenja pri svakom `Load unpacked`. Za produkciju:

1. Chrome Web Store dodjeljuje stabilni ID pri prvom upload-u
2. Taj ID se koristi u svim linkovima
3. Ekstenzija koristi `chrome.runtime.id` za samootkrivanje (ne hardkodirati)

## Protocol Versioning

Ekstenzija i backend trebaju da pregovaraju verziju protokola:

1. Backend šalje `supported_protocol_versions` u handshake odgovoru
2. Ekstenzija prijavljuje svoju verziju pri auth-u
3. Ako je ekstenzija prestara → `BROWSER_EXTENSION_VERSION_UNSUPPORTED` sa uputstvom za update
4. Ako je backend prestar → ekstenzija prikazuje "Update Ricky to continue"

Backward compatibility policy:
- Podržavati najmanje 2 prethodne verzije protokola
- Deprecation period: 3 mjeseca prije ukidanja stare verzije
- Breaking change = nova major verzija protokola

## Credential Storage Audit

### Ekstenzija strana
- `chrome.storage.local` — pairing credential, installation_id, profile metadata
- NIKAD u `localStorage`, `sessionStorage`, `indexedDB`, ili `window` global
- Podaci perzistiraju kroz restart browsera i service worker lifecycle
- Brišu se samo eksplicitnim `reset_pairing` ili deinstalacijom ekstenzije

### Backend strana
- `InstallCredential` — in-memory samo (nestaje na restart backend-a)
- `PairingSession` — in-memory, TTL 5 minuta
- Legacy secret fajl — `{data_dir}/browser_bridge_secret` (samo za backward compat)
- Nema perzistencije credentiala na disku
- Ekstenzija se mora ponovo autentifikovati nakon restarta backend-a

### Revocation
- `POST /connections/{profile_id}/revoke`:
  - Markira `revoked=True` u in-memory credential store
  - Zatvara WebSocket sa `4002: revoked`
  - Nakon revoke-a, ekstenzija ne može koristiti stari credential
  - Korisnik mora ponovo ući u pairing flow

## Privacy Red-Team Testovi

### Testovi koji su već pokriveni
- ✅ URL validacija: samo HTTP(S), bez `file://`, bez embedded credentials
- ✅ Incognito tabovi isključeni
- ✅ Nema čitanja sadržaja stranice (samo `chrome.tabs.query` metadata)
- ✅ Nema content scripts u manifestu
- ✅ `host_permissions: []` u manifestu
- ✅ Snapshot TTL 10s — tab metadata ne živi dugo

### Dodatne preporuke za C4 hardening
- [ ] Log redaction: URL-ovi u logovima skraćeni na origin
- [ ] Rate limiting: pairing pokušaji (max 5 u minuti)
- [ ] Audit log: svaki pairing/revoke/disconnect
- [ ] `PER_PAIRING_RATE_LIMIT` konstanta
- [ ] `chrome.storage.local` ne sadrži tab URL-ove ni u jednom trenutku
- [ ] Service worker ne loguje credential u console

## Produkcijski checklist

- [ ] Chrome Web Store developer registracija
- [ ] ZIP arhiva ekstenzije spremna za upload
- [ ] Store listing tekst (en + sr)
- [ ] Privacy policy URL
- [ ] Ikona 128x128
- [ ] Screenshot ekstenzije
- [ ] Edge Add-ons listing (ili Chrome Web Store link)
- [ ] Settings prikazuje store linkove u production modu
- [ ] Protocol version handshake implementiran
- [ ] Rate limiting za pairing endpoint
- [ ] Log redaction za URL-ove
- [ ] Verzija ekstenzije bump-ovana na 1.0.0
