# Streamlit Accounting ERP

This is a beginner-friendly Python accounting ERP prototype built with Streamlit, SQLite, SQLAlchemy, Pandas, OpenPyXL, and ReportLab.

## Features

- Dashboard with totals and recent records
- Cash Sales
- Credit Sales
- Vendors
- Purchases
- Payables
- Salaries
- Expenses
- Record listing and delete buttons
- Excel export for each module
- PDF export for each module
- SQLite persistence via SQLAlchemy

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

The SQLite file `erp_data.db` is created in the project folder automatically.
