# Loan Progress Report Dashboard

This repository contains a Streamlit dashboard for loan progress reporting.

## Deploy on Streamlit Cloud

1. Push this repository to GitHub.
2. Create a new app on Streamlit Cloud.
3. Set the main file to `streamlit_app.py`.
4. Streamlit Cloud will install dependencies from `requirements.txt`.

> The app now supports a shared default dataset:
> - visitors can open the app without uploading files by using the bundled demo data
> - an admin can upload real Bank + MIS CSV files and check the "Save this upload as the shared default dataset" option to make the dataset available for future visitors while the app is running
> - this is useful for Streamlit Cloud deployments where file uploader state is not shared automatically across sessions

## Local run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
