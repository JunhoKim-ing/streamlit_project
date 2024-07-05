import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

with open('./.streamlit/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
    )


conn = st.connection("gsheets", type=GSheetsConnection)

SEX_TYPES = ["Male", "Female", "Others"]


def read_data():
    data = conn.read(worksheet="sheet1", usecols=list(range(6)), ttl=3600)
    return data.dropna(how="all")

def write_data(data):
    conn.write(data)

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
    with st.form("Add New Student"):
        name = st.text_input("Name*")
        student_id = st.text_input("Student ID*")
        sex = st.selectbox("Sex*", options=SEX_TYPES, index=None)
        age = st.number_input("Age*", min_value=0)
        date_of_birth = st.date_input(label="Date of Birth", value=datetime.date(2000, 1, 1), min_value=datetime.date(1940,1,1))
        additional_notes = st.text_area(label="Additional Notes")

        st.markdown("**required*")

        if st.form_submit_button("Submit"):
            if not name or not student_id or not sex or not age or not date_of_birth:
                st.warning("Ensure all required information are filled.")
                st.stop()
            elif data["Student ID"].astype(str).str.contains(student_id).any():
                st.warning("A student with this ID already exists.")
                st.stop()
            else:
                new_data = pd.DataFrame([{
                    "Name": name,
                    "Student ID": student_id,
                    "Sex": sex,
                    "Age": age,
                    "Date of Birth": date_of_birth,
                    "Additional Notes": additional_notes
                }])

                updated_df = pd.concat([data, new_data], ignore_index=True)
                conn.update(worksheet="sheet1", data=updated_df)
                st.success("Student added successfully!")
                

def remove_data(data):
    st.header("Remove Student Data")
    target_student_id = st.text_input("Enter Student ID to remove:")

    if st.button("Remove Student"):
        data_filtered = data[data["Student ID"] == int(target_student_id)]
        if not data_filtered.empty:
            updated_df = data[data["Student ID"] != int(target_student_id)]
            conn.update(worksheet="sheet1", data=updated_df)
            st.success(f"Student with ID {target_student_id} removed successfully!")
        else:
            st.warning(f"No student found with ID {target_student_id}.")


def filter_search_data(data):
    st.header("Filter/Search Student Data")
    search_term = st.text_input("Search by name or student ID:")

    if st.button("Search"):
        filtered_data = data[data.apply(lambda row: search_term.lower() in row.astype(str).str.lower().values, axis=1)]
        st.dataframe(filtered_data)

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

    with st.container():
        st.title("Student Database Management")
        st.header("Current Student Data")
        st.dataframe(data)
        #if data_changed:
        #    st.dataframe(data)


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

    with st.container():
        st.title("Student Database Management")
        st.header("Current Student Data")
        st.dataframe(data)
        #if data_changed:
        #    st.dataframe(data)


    option = st.sidebar.selectbox(
        'Select an operation',
        ('View Data', 'Filter/Search')
    )
    
    if option == 'Filter/Search':
        filter_search_data(data)

if __name__ == "__main__":
    authenticator.login()
    main()

