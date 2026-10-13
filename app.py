import sqlite3
from pathlib import Path
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st


# -----------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------

st.set_page_config(
    page_title="Expense Tracker",
    page_icon="💰",
    layout="wide"
)


# -----------------------------------------------
# CUSTOM CSS
# -----------------------------------------------

st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #0f172a, #1e1b4b);
    color: #f8fafc;
}

h1, h2, h3 {
    color: #c4b5fd;
}

div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #312e81, #4338ca);
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #6366f1;
}

div[data-testid="stMetricLabel"] {
    color: #e0e7ff;
}

div[data-testid="stMetricValue"] {
    color: #ffffff;
}

.stButton > button {
    background-color: #7c3aed;
    color: white;
    border-radius: 8px;
    border: none;
}

.stButton > button:hover {
    background-color: #6d28d9;
    color: white;
}

section[data-testid="stSidebar"] {
    background-color: #111827;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------------------------
# DATABASE CONFIGURATION
# -----------------------------------------------

DATABASE_PATH = Path(__file__).resolve().parent / "expenses.db"


def get_connection():
    return sqlite3.connect(DATABASE_PATH)


def create_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_date TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                amount REAL NOT NULL,
                payment_method TEXT NOT NULL DEFAULT 'Cash'
            )
        """)

        # Check whether the existing table has payment_method
        columns = conn.execute(
            "PRAGMA table_info(expenses)"
        ).fetchall()

        column_names = [column[1] for column in columns]

        # Add the missing column without deleting existing expenses
        if "payment_method" not in column_names:
            conn.execute("""
                ALTER TABLE expenses
                ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'Cash'
            """)


def add_expense(expense_date, category, description, amount, payment_method):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO expenses
            (expense_date, category, description, amount, payment_method)
            VALUES (?, ?, ?, ?, ?)
        """, (
            expense_date.isoformat(),
            category,
            description,
            amount,
            payment_method
        ))


def get_expenses():
    with get_connection() as conn:
        return pd.read_sql_query(
            "SELECT * FROM expenses ORDER BY expense_date DESC, id DESC",
            conn
        )


def delete_expense(expense_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM expenses WHERE id = ?",
            (int(expense_id),)
        )


create_table()


# -----------------------------------------------
# APP TITLE
# -----------------------------------------------

st.title("💰 Expense Tracker")
st.caption("Track your money. Understand your spending. Save smarter.")

st.divider()


# -----------------------------------------------
# SIDEBAR: ADD EXPENSE
# -----------------------------------------------

with st.sidebar:
    st.header("➕ Add New Expense")

    with st.form("expense_form", clear_on_submit=True):

        expense_date = st.date_input(
            "Expense Date",
            value=date.today(),
            max_value=date.today()
        )

        category = st.selectbox(
            "Category",
            [
                "Food",
                "Travel",
                "Shopping",
                "Bills",
                "Education",
                "Health",
                "Entertainment",
                "Groceries",
                "Other"
            ]
        )

        description = st.text_input(
            "Description",
            placeholder="e.g. Lunch with friends"
        )

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            value=100.0,
            step=10.0
        )

        payment_method = st.selectbox(
            "Payment Method",
            [
                "Cash",
                "UPI",
                "Debit Card",
                "Credit Card",
                "Net Banking",
                "Other"
            ]
        )

        submitted = st.form_submit_button(
            "➕ Add Expense",
            width="stretch"
        )

        if submitted:
            add_expense(
                expense_date,
                category,
                description.strip(),
                amount,
                payment_method
            )

            st.success("Expense added successfully!")
            st.rerun()


# -----------------------------------------------
# LOAD EXPENSE DATA
# -----------------------------------------------

expenses = get_expenses()

if not expenses.empty:
    expenses["expense_date"] = pd.to_datetime(
        expenses["expense_date"],
        errors="coerce"
    )

    expenses = expenses.dropna(
        subset=["expense_date", "amount"]
    ).copy()

    expenses["month"] = expenses["expense_date"].dt.strftime("%Y-%m")

    expenses["month_label"] = expenses["expense_date"].dt.strftime("%B %Y")


# -----------------------------------------------
# MONTH FILTER
# -----------------------------------------------

st.subheader("📅 Filter Expenses")

if expenses.empty:
    filtered_expenses = expenses.copy()
    st.info("No expenses yet. Add your first expense using the form in the sidebar.")

else:
    available_months = sorted(
        expenses["month"].unique().tolist(),
        reverse=True
    )

    month_options = ["All Months"] + available_months

    selected_month = st.selectbox(
        "Select Month",
        month_options
    )

    if selected_month == "All Months":
        filtered_expenses = expenses.copy()
    else:
        filtered_expenses = expenses[
            expenses["month"] == selected_month
        ].copy()


# -----------------------------------------------
# SUMMARY CARDS
# -----------------------------------------------

total_spending = float(filtered_expenses["amount"].sum())

transaction_count = len(filtered_expenses)

average_expense = (
    float(filtered_expenses["amount"].mean())
    if transaction_count > 0
    else 0.0
)

today = pd.Timestamp(date.today())

if expenses.empty:
    current_month_spending = 0.0
else:
    current_month_expenses = expenses[
        (expenses["expense_date"].dt.year == today.year)
        & (expenses["expense_date"].dt.month == today.month)
    ]

    current_month_spending = float(
        current_month_expenses["amount"].sum()
    )


col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "💰 Total Spending",
    f"₹{total_spending:,.2f}"
)

col2.metric(
    "📅 This Month",
    f"₹{current_month_spending:,.2f}"
)

col3.metric(
    "🧾 Transactions",
    transaction_count
)

col4.metric(
    "📊 Average Expense",
    f"₹{average_expense:,.2f}"
)


# -----------------------------------------------
# CATEGORY ANALYSIS
# -----------------------------------------------

st.divider()
st.subheader("🍩 Spending by Category")

if filtered_expenses.empty:
    st.info("Add expenses to see your category analysis.")

else:
    category_totals = (
        filtered_expenses
        .groupby("category", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
    )

    fig_category = px.pie(
        category_totals,
        names="category",
        values="amount",
        title="Category-Wise Spending",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Vivid
    )

    fig_category.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1f5f9",
        title_x=0.02,
        legend_title_text="Category"
    )

    st.plotly_chart(
        fig_category,
        width="stretch"
    )


# -----------------------------------------------
# MONTHLY SPENDING CHART
# -----------------------------------------------

st.divider()
st.subheader("📈 Monthly Spending Trend")

if expenses.empty:
    st.info("Your monthly spending chart will appear after you add expenses.")

else:
    monthly_totals = (
        expenses
        .assign(
            month_start=expenses["expense_date"].dt.to_period("M").dt.to_timestamp()
        )
        .groupby("month_start", as_index=False)["amount"]
        .sum()
        .sort_values("month_start")
    )

    fig_monthly = px.bar(
        monthly_totals,
        x="month_start",
        y="amount",
        title="Monthly Expenses",
        labels={
            "month_start": "Month",
            "amount": "Amount (₹)"
        },
        text_auto=".2s"
    )

    fig_monthly.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font_color="#f1f5f9",
        title_x=0.02
    )

    st.plotly_chart(
        fig_monthly,
        width="stretch"
    )


# -----------------------------------------------
# TRANSACTION HISTORY
# -----------------------------------------------

st.divider()
st.subheader("📋 Transaction History")

if filtered_expenses.empty:
    st.info("No transactions available for the selected filter.")

else:
    display_expenses = filtered_expenses[
        [
            "id",
            "expense_date",
            "category",
            "description",
            "amount",
            "payment_method"
        ]
    ].copy()

    display_expenses["expense_date"] = (
        display_expenses["expense_date"].dt.strftime("%d-%m-%Y")
    )

    display_expenses = display_expenses.rename(
        columns={
            "id": "ID",
            "expense_date": "Date",
            "category": "Category",
            "description": "Description",
            "amount": "Amount (₹)",
            "payment_method": "Payment Method"
        }
    )

    st.dataframe(
        display_expenses,
        width="stretch",
        hide_index=True
    )


# -----------------------------------------------
# DELETE EXPENSE
# -----------------------------------------------

st.divider()
st.subheader("🗑️ Delete an Expense")

if expenses.empty:
    st.info("There are no expenses to delete.")

else:
    expense_options = {
        f"#{int(row.id)} | {row.expense_date.strftime('%d-%m-%Y')} | "
        f"{row.category} | ₹{row.amount:.2f} | {row.description or 'No description'}":
        int(row.id)
        for row in expenses.itertuples()
    }

    selected_expense_label = st.selectbox(
        "Select a transaction to delete",
        list(expense_options.keys())
    )

    if st.button("🗑️ Delete Selected Expense"):
        delete_expense(
            expense_options[selected_expense_label]
        )

        st.success("Expense deleted successfully!")
        st.rerun()


# -----------------------------------------------
# FOOTER
# -----------------------------------------------

st.divider()

st.markdown(
    "<div style='text-align:center; color:#a5b4fc;'>"
    "💜 Built with Python, Streamlit, SQLite and Plotly"
    "</div>",
    unsafe_allow_html=True
)