import streamlit as st
from menu import menu

# initialize st.session_state.role to None
if "role" not in st.session_state:
    st.session_state["role"] = None

# retrieve the role from Session State to initialize the widget
st.session_state["_role"] = st.session_state["role"]


def set_role():
    # callback function to save the role selection to Session State
    st.session_state["role"] = st.session_state["_role"]


# select to choose role
st.selectbox(label="Select your role:", options=[None, "user", "admin", "super-admin"],
             key="_role", on_change=set_role)

menu()  # render the dynamic menu
