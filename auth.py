"""
Authentication module for EV Engine Streamlit dashboard.

This module provides simple password-based authentication to protect
the dashboard from unauthorized access and prevent API quota abuse.
"""

import streamlit as st
import hmac


def check_password() -> bool:
    """Returns `True` if the user has entered the correct password.

    Uses Streamlit secrets management to store passwords securely.
    Implements session state to remember authentication status.

    Returns:
        True if password is correct, False otherwise

    Examples:
        >>> # In dashboard.py
        >>> if not check_password():
        >>>     st.stop()  # Stop execution if not authenticated
    """

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(
            st.session_state["password"],
            st.secrets["passwords"]["admin"]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.markdown("### 🔐 EV Scout - Login Required")
    st.markdown("Please enter your password to access the dashboard.")

    st.text_input(
        "Password",
        type="password",
        on_change=password_entered,
        key="password",
        help="Enter the password configured in your secrets"
    )

    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect. Please try again.")

    st.markdown("---")
    st.caption("💡 Tip: Password is configured in .streamlit/secrets.toml")

    return False


def add_logout_button():
    """Adds a logout button to the sidebar.

    Call this function in your dashboard to allow users to log out.

    Examples:
        >>> # In dashboard.py sidebar
        >>> add_logout_button()
    """
    with st.sidebar:
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state["password_correct"] = False
            st.rerun()
