import streamlit as st

class Concept():
    def body(self, images):
        for image in images:
            st.image(image, use_column_width=True)