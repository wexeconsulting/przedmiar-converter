import streamlit as st
from streamlit_extras.stylable_container import stylable_container
import requests
import os
import base64

token = f"Bearer {os.getenv('TOKEN')}"


def main():
    # page
    st.set_page_config(layout="centered", page_title="PDF Konwerter")
    st.image('przedmiar_logo.png', width=300)
    st.title('PDF Konwerter')

    # upload widget
    add_file_uploader()

    # create button
    add_button()

def add_file_uploader():
    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0

    uploaded_file = st.file_uploader(
        label="Wybierz plik do załadowania", 
        accept_multiple_files=False,
        key=f"uploader_{st.session_state.uploader_key}",
        help="Wybierz plik")

    if uploaded_file is not None:
        st.session_state.k_uploader = uploaded_file

def add_button():
    with stylable_container(key="cnt_but_submit", css_styles="""
        {
            [data-testid="baseButton-secondary"] {
            background-color: green;
            }
        }
        """):
        if st.button(label="Konwertuj", key="k_but_submit"):
            submit_form()

def submit_form():
    if 'k_uploader' not in st.session_state or st.session_state.k_uploader is None:
        st.error('Nie wybrano pliku')
        return

    backend_url = 'https://127.0.0.1:5000'

    # Send the file to the backend
    with st.spinner('Przetwarzanie...'):
        file = st.session_state.k_uploader
        files = {'file': (file.name, file.getvalue(), file.type)}
        headers = {'Authorization': token}
        response = requests.post(f'{backend_url}/latest/converttocsv', files=files, headers=headers, verify=False)

        if response.status_code == 200:
            st.success('Plik został pomyślnie przekonwertowany')
            st.download_button(
                label="Pobierz przekonwertowany plik",
                data=response.content,
                file_name='output.csv',
                mime='text/csv'
            )
            # Increment the uploader key to reset the file uploader
            st.session_state.uploader_key += 1
            st.session_state.k_uploader = None
        else:
            st.error(f'System nie wspiera konwersji tego pliku')

if __name__ == '__main__':
    main()