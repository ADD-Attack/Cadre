# Ticket 001 — Hour-by-hour weather page

- state: spec-done
- opened: 2026-10-14 by the owner (seeded by the operator from the owner's project-ideas list)
- station_history: 2026-10-14 18:24 UTC — Spec station: spec written, state queued → spec-done
- live_url: (none yet)
- receipt: (none yet)

## Order

A single web page that shows the next 24 hours of weather for Kansas City,
hour by hour: temperature, chance of precipitation, and feels-like
temperature, so the owner can see at a glance when rain is coming and how
the day will actually feel. It should load fast, work on a phone, and need
no account and no API key.

## Spec

**Product, restated:** A single self-contained HTML page that fetches Kansas
City's next 24 hours of weather from the Open-Meteo API in the browser and
renders one row per hour showing the hour, the temperature, the precipitation
chance, and the feels-like temperature.

### Acceptance claims

1. The product is one self-contained HTML file committed at
   `the-line/products/weather/index.html` in the Cadre repo. It requires no
   build step and no other local files; its only external network dependency
   is the weather API call.
2. When the page is rendered, it displays exactly 24 hourly rows: one for
   each of the next 24 hours starting from the current hour in
   America/Chicago, in chronological order.
3. Each hourly row shows four values: the hour as a local time label, the
   temperature in °F, the precipitation probability as a percentage, and the
   feels-like (apparent) temperature in °F.
4. The hourly rows are generated from the API response at page load, not
   hard-coded into the HTML: the shipped file contains no static table of
   24 pre-written weather values.
5. Weather data is fetched client-side from the Open-Meteo forecast API
   (`api.open-meteo.com/v1/forecast`) with no API key, token, or other
   credential in the request or anywhere in the shipped file, and the page
   renders the full table for a first-time visitor with no sign-in.
6. The API request targets Kansas City, MO, using latitude 39.0997 and
   longitude -94.5786, and requests the hourly variables
   `temperature_2m`, `apparent_temperature`, and `precipitation_probability`.
7. Temperatures are requested and displayed in Fahrenheit: the API request
   includes `temperature_unit=fahrenheit`, and displayed temperatures are
   labeled °F.
8. The page includes a viewport meta tag, and rendered at a 390 px-wide
   viewport the hourly table is fully readable with no horizontal
   scrolling.
9. The shipped HTML file is under 50 KB, and loading the page makes no
   network requests other than the single weather API call.
10. If GitHub Pages is enabled on the housing repo, the page is reachable
    at https://add-attack.github.io/Cadre/the-line/products/weather/ and
    returns HTTP 200 serving this page. (Pages enablement is currently
    unverified; claims 1–9 stand on the committed artifact alone.)

### Sensor markers

Exact strings the sensor should find in the shipped HTML:

- Claim 5: `api.open-meteo.com/v1/forecast`
- Claim 6: `39.0997`, `-94.5786`, `temperature_2m`, `apparent_temperature`,
  `precipitation_probability`
- Claim 7: `temperature_unit=fahrenheit`
- Claim 8: `name="viewport"`

### Out of scope

- Forecasts beyond the next 24 hours (daily/multi-day views)
- Any location other than Kansas City, or a location picker/search
- Severe-weather alerts, radar, or maps
- Historical weather
- User accounts, sign-in, or saved preferences
- Any backend, server-side code, or data persistence/caching layer
- A native or installable mobile app

### Build notes (constraints)

- Commit the product at `the-line/products/weather/index.html` in the Cadre
  repo (The Line currently lives as a folder inside that repo).
- Single HTML file with inline CSS and JavaScript; no framework, bundler,
  or build step.
- Data source is the Open-Meteo forecast API, fetched client-side, no key.
  Use `timezone=America/Chicago` in the request so the 24 hours align to
  Kansas City local time.
- Whether GitHub Pages is enabled on the housing repo is unverified, so
  every core claim must be checkable against the committed HTML artifact
  itself; do not rely on any server-side behavior.

## Build notes

(To be written by the Build station.)

## Verification

(To be written by the Verify station, one verdict per acceptance claim.)
