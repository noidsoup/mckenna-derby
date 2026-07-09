# Deploy McKenna Derby to Streamlit Community Cloud

Share the interactive dashboard with a friend via a private GitHub repo and optional shared password.

## Prerequisites

- GitHub repo: https://github.com/noidsoup/mckenna-derby (private is fine)
- [Streamlit Community Cloud](https://share.streamlit.io/) account (sign in with GitHub)
- Grant Streamlit access to the `noidsoup/mckenna-derby` repo when prompted

## Deploy steps

1. Open **https://share.streamlit.io/** and click **Create app**
2. **Repository:** `noidsoup/mckenna-derby`
3. **Branch:** `main`
4. **Main file path:** `dashboard.py`
5. Click **Advanced settings**
   - **Python version:** 3.11 (or leave default if `runtime.txt` is detected)
6. Open **Secrets** and paste (set your own password):

```toml
[dashboard]
password = "your-shared-password-here"
```

7. Click **Deploy**

First build takes a few minutes (`pip install` from `requirements.txt`).

## Share with your friend

Send them:

- The app URL (e.g. `https://mckenna-derby-xxxx.streamlit.app`)
- The shared password from secrets (not in git)

They open the link, enter the password once per browser session, then use the dashboard.

## What works on Cloud

| Feature | Cloud |
|---------|-------|
| Hong Kong bundled (default) | Yes (`mckenna_derby/datasets/hk_runners.csv`) |
| Synthetic demo (Advanced) | Yes |
| Upload CSV (Advanced) | Yes |
| Raw Kaggle `rawdata/` | No (gitignored; not needed) |
| Password gate | Yes (via secrets) |

## Local password testing

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit password, then:
streamlit run dashboard.py
```

## Updating the live app

Push to `main` on GitHub — Streamlit redeploys automatically.

```bash
git push origin main
```

## Troubleshooting

- **Import errors:** Ensure `requirements.txt` starts with `.` so `mckenna_derby` installs from `pyproject.toml`
- **Secrets not applied:** Re-save secrets in the app dashboard and **Reboot app**
- **Repo not listed:** GitHub → Settings → Applications → Streamlit → grant access to `mckenna-derby`
