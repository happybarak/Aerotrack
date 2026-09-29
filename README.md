# AeroTrack — Air Quality Index Visualization

A Streamlit web app for monitoring and exploring Air Quality Index (AQI)
data across Indian cities, with a Power BI dashboard embedded inside it.

## What it does

- Users create an account or log in (email + password).
- Once logged in, they see:
  - A project description (purpose, significance, who it's for).
  - An embedded Power BI dashboard.
  - Buttons to expand the dashboard, or download it as PDF / PBIX.
  - A filterable data table (by City, Year, AQI) pulled from the raw CSV.
  - A logout button.

## Tech stack

| Piece            | Tool                          |
|-------------------|-------------------------------|
| Web app / UI       | Streamlit                    |
| Data handling      | pandas                       |
| User accounts      | SQLite (`users.db`)          |
| Password security  | PBKDF2 (salted, 200k iters)  |
| AQI data           | CSV (`aqi_data.csv`)         |
| Visualization      | Power BI (embedded iframe)   |

## Project files

```
aqi.py                  # the entire app — UI, auth, filtering
aqi_data.csv             # raw AQI dataset (CITY, DATE, AQI, pollutants...)
AQI_Dashboard.pdf         # exported dashboard, offered as a download
AQI_Visualization.pbix    # Power BI source file, offered as a download
users.db                  # created automatically on first run
```

## How it works (process)

1. **App starts** → `st.set_page_config()` sets the page title, then
   `init_db()` connects to `users.db` and creates the `users` table if
   it doesn't exist yet (columns: `email`, `username`, `name`, `salt`,
   `password_hash`).

2. **Sign Up** → user fills the form → `add_user()` generates a random
   salt, derives a PBKDF2 hash of the password with that salt, and
   inserts `(email, username, name, salt, password_hash)` into
   `users.db`. If the email already exists, signup fails cleanly
   (no duplicate accounts).

3. **Login** → user enters email + password → `authenticate_user()`
   looks up the row by email, re-derives a hash using the *stored*
   salt and the entered password, and compares it to the stored hash.
   Match → `st.session_state['authentication_status'] = True` and the
   app reruns into the logged-in view. No match → error shown, user
   stays on the login form.

4. **Logged-in view** → runs top to bottom on every interaction
   (this is how Streamlit works — the whole script re-executes):
   - `description()` renders the static "About / Significance / Who
     can use / Use cases" text.
   - `dashboard()` embeds the Power BI report via an `<iframe>`.
   - `aqi_data.csv` is loaded fresh into a pandas DataFrame.
   - Download buttons stream `AQI_Dashboard.pdf` and
     `AQI_Visualization.pbix` straight from disk.
   - The filters section builds a `Year` column from `DATE`, then lets
     the user multiselect City / Year / AQI. Selecting any filter
     narrows the DataFrame with a pandas boolean mask; the resulting
     table is shown with `st.dataframe()`.

5. **Logout** → clears `authentication_status` and reruns the app,
   dropping the user back to the Login/Sign Up screen.

## Setup

```bash
pip install streamlit pandas
streamlit run aqi.py
```

No extra build step — `users.db` is created automatically the first
time you run the app. Just make sure `aqi_data.csv`,
`AQI_Dashboard.pdf`, and `AQI_Visualization.pbix` are in the same
folder as `aqi.py`.

## Notes on security

Passwords are never stored in plain text or as a bare hash. Each user
gets a random 16-byte salt, and the password is run through PBKDF2
(SHA-256, 200,000 iterations) before being stored. This means:

- Two users with the same password get *different* stored hashes.
- Even if `users.db` leaked, cracking a password requires brute-forcing
  it individually — a precomputed rainbow table won't work.
