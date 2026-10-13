import streamlit as st

st.title("Expense Tracker")
st.write("Testing the application.")

name = st.text_input("Enter your name")

if name:
    st.success(f"Hello, {name}!")

st.button("Test Button")