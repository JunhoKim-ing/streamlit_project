import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth
from st_files_connection import FilesConnection
import yaml
from yaml.loader import SafeLoader


conn_config = st.connection('gcs', type=FilesConnection)
config = conn_config.read("config.json", input_format="json", ttl=600)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
    )

conn_gsheet = st.connection("gsheets", type=GSheetsConnection)

SEX_TYPES = ["Male", "Female", "Others"]


def read_data():
    data = conn_gsheet.read(worksheet="sheet1", usecols=list(range(6)), ttl=5)
    data = data.dropna(how="all")
    data['Date of Birth'] = pd.to_datetime(data['Date of Birth'], errors='coerce').dt.strftime('%Y/%m/%d')
    data['Student ID'] = data['Student ID'].astype(str)
    data['Student ID'] = data['Student ID'].apply(lambda x: x.split('.')[0] if '.' in x else x)
    return data

def write_data(data):
    data['Date of Birth'] = pd.to_datetime(data['Date of Birth'], errors='coerce').dt.strftime('%Y/%m/%d')
    data['Student ID'] = data['Student ID'].astype(str)
    data['Student ID'] = data['Student ID'].apply(lambda x: x.split('.')[0] if '.' in x else x)
    conn_gsheet.write(data)
    
def main():
    if st.session_state["authentication_status"]:
        st.write(f'Welcome *{st.session_state["name"]}*')
        st.title('Some content')
        try:
            if authenticator.update_user_details(st.session_state["username"]):
                print(st.session_state['username'])
                with open('./.streamlit/config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                st.success('Entries updated successfully')
        except Exception as e:
            st.error(e)
        if config["credentials"]["usernames"][st.session_state["name"]]["email"] in config["pre-authorized"]["emails"]:
            admin()
        else:
            viewer()

        authenticator.logout()


    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
        help()
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')
        help()


def add_data(data):
    st.header("Add New Student")
    required_fields = ["Name", "Student ID", "Sex", "Age", "Date of Birth"]

    with st.form("Add New Student"):
        inputs = {
            "Name": st.text_input("Name*"),
            "Student ID": st.text_input("Student ID*"),
            "Sex": st.selectbox("Sex*", options=SEX_TYPES, index=None),
            "Age": st.number_input("Age*", min_value=0, max_value=120),
            "Date of Birth": st.date_input(
                label="Date of Birth",
                value=datetime.date(2000, 1, 1),
                min_value=datetime.date(1950, 1, 1),
                max_value=datetime.date.today()
            ),
            "Additional Notes": st.text_area(label="Additional Notes")
        }

        st.markdown("**required*")

        if st.form_submit_button("Submit"):
            for field in required_fields:
                if inputs[field] is None or (isinstance(inputs[field], str) and inputs[field].strip() == ""):
                    st.warning(f"Ensure all required information are filled. {field} is required.")
                    st.stop()

            if data["Student ID"].astype(str).str.contains(inputs["Student ID"]).any():
                st.warning("A student with this ID already exists.")
                st.stop()

            new_data = pd.DataFrame([{
                "Name": inputs["Name"],
                "Student ID": inputs["Student ID"],
                "Sex": inputs["Sex"],
                "Age": inputs["Age"],
                "Date of Birth": inputs["Date of Birth"].strftime('%Y/%m/%d'),  # Format the date
                "Additional Notes": inputs["Additional Notes"]
            }])

            updated_df = pd.concat([data, new_data], ignore_index=True)
            conn_gsheet.update(worksheet="sheet1", data=updated_df)
            st.success("Student added successfully!")
                

def remove_data(data):
    st.header("Remove Student Data")
    target_student_id = st.text_input("Enter Student ID to remove:")

    if st.button("Remove Student"):
        data_filtered = data[data["Student ID"] == target_student_id]
        if not data_filtered.empty:
            updated_df = data[data["Student ID"] != target_student_id]
            conn_gsheet.update(worksheet="sheet1", data=updated_df)
            st.success(f"Student with ID {target_student_id} removed successfully!")
        else:
            st.warning(f"No student found with ID {target_student_id}.")


def filter_search_data(data):
    st.header("Filter/Search Student Data")
    search_term = st.text_input("Search by name or student ID:")

    if st.button("Search"):
        filtered_data = data[data.apply(lambda row: search_term.lower() in row.astype(str).str.lower().values, axis=1)]
        filtered_data.index += 1
        st.dataframe(filtered_data, height=300)

def help():
    option = st.selectbox('Help?', ['--Select--', 'Forgot username', 'Forgot password', 'New register'])

    if option == 'Forgot password':
        try:
            username_of_forgotten_password, email_of_forgotten_password, new_random_password = authenticator.forgot_password()
            if username_of_forgotten_password:
                #############
                with open('./.streamlit/config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                st.success('New password to be sent to your email')
            elif username_of_forgotten_password == False:
                st.error('Username not found')
        except Exception as e:
            st.error(e)

    elif option == 'Forgot username':
        try:
            username_of_forgotten_username, email_of_forgotten_username = authenticator.forgot_username()
            if username_of_forgotten_username:
                ##############
                st.success('Username to be sent to your email')
            elif username_of_forgotten_username == False:
                st.error('Email not found')
        except Exception as e:
            st.error(e)

    elif option == 'New register':
        try:
            email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user(pre_authorization=False)
            if email_of_registered_user:
                with open('./.streamlit/config.yaml', 'w') as file:
                    yaml.dump(config, file, default_flow_style=False)
                st.success('User registered successfully')
        except Exception as e:
            st.error(e)


def admin():
    data = read_data()
    data.index += 1

    with st.container():
        st.title("Student Database Management")
        st.header("Current Student Data")
        st.dataframe(data, height=300)
        #if data_changed:
        #    st.dataframe(data, height=300)


    option = st.sidebar.selectbox(
        'Select an operation',
        ('View Data', 'Add Data', 'Remove Data', 'Filter/Search')
    )

    if option == 'Add Data':
        add_data(data)
    elif option == 'Remove Data':
        remove_data(data)
    elif option == 'Filter/Search':
        filter_search_data(data)

def viewer():
    data = read_data()
    data.index += 1

    with st.container():
        st.title("Student Database Management")
        st.header("Current Student Data")
        st.dataframe(data, height=300)
        #if data_changed:
        #    st.dataframe(data, height=300)


    option = st.sidebar.selectbox(
        'Select an operation',
        ('View Data', 'Filter/Search')
    )
    
    if option == 'Filter/Search':
        filter_search_data(data)

if __name__ == "__main__":
    authenticator.login()
    main()

