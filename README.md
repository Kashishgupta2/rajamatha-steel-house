# 🏪 Rajamatha Steel House – Sales Management System

Streamlit app that connects directly to your existing MySQL database **`rajamatha`**.
The app reads the table and column names from MySQL itself (no CSV / import script needed).

Expected columns (names matched ignoring case, spaces and underscores):
Product, Product_Type, Quantity_Sold, Selling_Price, Discount, Final_Sales, Cost_Price, Profit, Payment_Type

- If the table has no primary key, the app adds an auto-increment `row_id` on first run (needed for update/delete). Existing data is untouched.
- `Final_Sales = Quantity_Sold × Selling_Price − Discount`; `Profit = Final_Sales − Quantity_Sold × Cost_Price` (recalculated on every add/update).

## Run
```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # set host/user/password
python test_connection.py      # optional: lists tables + columns found
streamlit run app.py
```
