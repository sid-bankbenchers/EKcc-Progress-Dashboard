# Loan Progress Report Dashboard

This repository contains a Streamlit dashboard for loan progress reporting.

## Deploy on Streamlit Cloud

1. Push this repository to GitHub.
2. Create a new app on Streamlit Cloud.
3. Set the main file to `streamlit_app.py`.
4. Streamlit Cloud will install dependencies from `requirements.txt`.

> The app now supports a shared default dataset:
> - visitors can open the app without uploading files by using the bundled demo dataset or the saved shared dataset
> - an administrator can upload real Bank + MIS CSV files and save them as the shared default dataset for all visitors
> - the admin password can be configured with `st.secrets["admin_password"]` or the `ADMIN_PASSWORD` environment variable; the default is `admin123`
> - this makes the dataset available across visitors while the deployment is running

## Local run

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
