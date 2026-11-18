import streamlit as st

def add_custom_css():
    st.markdown("""
        <style>
        /* Body and App Background */
        body, .stApp {
            background-color: #121212;
            color: #e0e0e0;
        }

        /* Main Title */
        .main-title {
            font-size: 36px;
            font-weight: bold;
            color: #ffffff;
            text-align: center;
            padding: 10px;
            border-bottom: 2px solid #29b6f6;
            margin-bottom: 20px;
        }

        /* Subtitles and Section Titles */
        h2, h3 {
            color: #29b6f6;
            margin-top: 20px;
        }

        /* General Text */
        p, label {
            color: #e0e0e0;
        }

        /* Table Styling */
        table {
            background-color: #1e1e1e;
            color: #e0e0e0;
            border-collapse: collapse;
            width: 100%;
            border-radius: 10px;
            overflow: hidden;
        }

        th, td {
            border: 1px solid #444444;
            padding: 12px;
            text-align: left;
            color: #f5f5f5;
            font-size: 14px;
        }

        th {
            background-color: #29b6f6;
            color: #e0e0e0;
            font-weight: bold;
        }

        tr:nth-child(even) {
            background-color: #white;
        }

        tr:nth-child(odd) {
            background-color: #white;
        }

        tr:hover {
            background-color: #3333;
        }

        /* Input Elements */
        .stTextInput > div, .stSelectbox > div, .stButton > button {
            background-color: #1c1c1c !important;
            color: #e0e0e0 !important;
            border: 1px solid #444444;
            border-radius: 10px;
        }

        /* Buttons */
        .stButton > button {
            background-color: #29b6f6 !important;
            color: white !important;
            border-radius: 10px;
            padding: 10px;
            font-size: 16px;
            transition: background-color 0.3s ease;
        }

        .stButton > button:hover {
            background-color: #0288d1 !important;
        }

        /* Scrollbar Styling */
        ::-webkit-scrollbar {
            width: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #2e2e2e;
        }
        ::-webkit-scrollbar-thumb {
            background: #29b6f6;
            border-radius: 10px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #0288d1;
        }

        /* Streamlit Widgets Fix for Dark Mode */
        .stTextInput > div > input, .stSelectbox > div > div {
            background-color: #1c1c1c !important;
            color: #e0e0e0 !important;
        }
        </style>
    """, unsafe_allow_html=True)