# Scrape dummy images from Unsplash via CSV

Python script that reads a CSV, uses one column (e.g. `city_name`) as a search term for [Unsplash](https://unsplash.com), and downloads the **first free image** (top-left of results) for each row. Saves files as `{value}.jpeg` (e.g. `amsterdam.jpeg`).

Runs in a **real browser** (visible by default) with **random delays** between actions and between rows to mimic a human and reduce the chance of being blocked.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
python scrape_unsplash_from_csv.py sample_locations.csv --column city_name
```

- **Input:** CSV path and the column to use as the search term (e.g. `city_name`).
- **Output:** Images in `downloaded_images/` by default (e.g. `amsterdam.jpeg`, `paris.jpeg`).

Options:

- `-o, --output-dir DIR` — Directory to save images (default: `downloaded_images`).
- `--headless` — Run browser in the background (no window).
- `--slow MS` — Slowness in ms (default: 150); higher = slower, more human-like.

Example with custom output dir:

```bash
python scrape_unsplash_from_csv.py my_cities.csv -c city_name -o ./images
```

## Behavior

- Opens `https://unsplash.com/s/photos/{search_term}` for each row.
- Waits for the page to load, then finds the **first free** “Download” link (skips Unsplash+ locked images).
- Downloads that image and saves it as `{sanitized_value}.jpeg`.
- Uses random pauses (about 2–5 s after load, 4–10 s between rows) and a visible browser to look like normal use.
- Skips rows where the output file already exists.

## CSV format

Any CSV with a header row; the column you pass with `--column` must exist. Example:

```csv
city_name,country,notes
amsterdam,Netherlands,Canals
paris,France,Eiffel Tower
```

## License / terms

Unsplash images are subject to [Unsplash’s license](https://unsplash.com/license). Use this script responsibly and in line with their terms of service.
