import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit_authenticator as stauth



conn_gsheet = st.connection("gsheets", type=GSheetsConnection)

users = conn_gsheet.read(worksheet="users", usecols=list(range(6)), ttl=5)
users = users.set_index(users.keys()[0])

config = {
    'credentials' : {'usernames' : users.to_dict('index')},
    'pre-authorized' : {'emails' : conn_gsheet.read(worksheet="pre-authorized", usecols=list(range(1)), ttl=5)['emails'].to_list()},
    'cookie' : conn_gsheet.read(worksheet="cookie", usecols=list(range(3)), ttl=5).to_dict('records')[0]
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['pre-authorized']
    )

SEX_TYPES = ["Male", "Female", "Others"]
SECTOR_TYPES = ["Computer & Information Technology", "Electricity Installation", "Administration & Accounting", "Cooking & Service",
                "Beauty & Hair Dressing", "Sewing", "Install & Repair Air Conditioner", "Others"]

def read_data():
    def calculate_age(born):
        today = datetime.date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    
    data = conn_gsheet.read(worksheet="sheet1", usecols=list(range(8)), ttl=5)
    data = data.dropna(how="all")
    data['Date of Birth'] = pd.to_datetime(data['Date of Birth'], errors='coerce')
    data['Age'] = data['Date of Birth'].apply(calculate_age)
    data['Date of Birth'] = data['Date of Birth'].dt.strftime('%Y/%m/%d')

    data['Student ID'] = data['Student ID'].astype(str)
    data['Student ID'] = data['Student ID'].apply(lambda x: x.split('.')[0] if '.' in x else x)
    data['Phone Number'] = data['Phone Number'].astype(str)
    data['Phone Number'] = data['Phone Number'].apply(lambda x: x.split('.')[0] if '.' in x else x)
    
    age_column = data.pop('Age')
    data.insert(3, 'Age', age_column)
    return data

def write_data(data):
    data['Date of Birth'] = pd.to_datetime(data['Date of Birth'], errors='coerce').dt.strftime('%Y/%m/%d')
    data['Student ID'] = data['Student ID'].astype(str)
    data['Student ID'] = data['Student ID'].apply(lambda x: x.split('.')[0] if '.' in x else x)
    data['Phone Number'] = data['Phone Number'].astype(str)
    data['Phone Number'] = data['Phone Number'].apply(lambda x: x.split('.')[0] if '.' in x else x)
    conn_gsheet.write(data)
    
def main():
    if st.session_state["authentication_status"]:
        st.write(f'Welcome *{st.session_state["name"]}*')
        try:
            if authenticator.update_user_details(st.session_state["username"]):
                renew_user_inforamtion()
                print(st.session_state['username'])
                st.success('Entries updated successfully')
        except Exception as e:
            st.error(e)
        st.success(config == authenticator.authentication_contraller.authentication_model.credentials)
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

def renew_user_information():
    config['credentials'] = authenticator.authentication_contraller.authentication_model.credentials
    users = pd.DataFrame(config['credentials']['usernames']).transpose()
    users = pd.concat([pd.DataFrame({'id':users.index}, index=users.index), users], axis=1)
    conn_gsheet.update(worksheet="users", data=users)

def add_data(data):
    st.header("Add New Student")
    required_fields = ["Student ID", "Name", "Sex", "Date of Birth", "Sector"]

    with st.form("Add New Student"):
        inputs = {
            "Student ID": st.text_input("Student ID*"),
            "Name": st.text_input("Name*"),
            "Sex": st.selectbox("Sex*", options=SEX_TYPES, index=None),
            "Date of Birth": st.date_input(
                label="Date of Birth*",
                value=datetime.date(2000, 1, 1),
                min_value=datetime.date(1950, 1, 1),
                max_value=datetime.date.today()
            ),
            "Phone Number": st.text_input("Phone Number (Ex. 000-0000-0000)"),
            "Sector": st.selectbox("Sector*", options=SECTOR_TYPES, index=None),
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
                "Student ID": inputs["Student ID"],
                "Name": inputs["Name"],
                "Sex": inputs["Sex"],
                "Date of Birth": inputs["Date of Birth"].strftime('%Y/%m/%d'),  # Format the date
                "Phone Number": inputs["Phone Number"],
                "Sector": inputs["Sector"],
                "Additional Notes": inputs["Additional Notes"]
            }])

            updated_df = pd.concat([data, new_data], ignore_index=True)
            updated_df = updated_df.drop(columns=['Age'])
            
            conn_gsheet.update(worksheet="sheet1", data=updated_df)
            st.success("Student added successfully!")
                

def remove_data(data):
    st.header("Remove Student Data")
    target_student_id = st.text_input("Enter Student ID to remove:")

    if st.button("Remove Student"):
        data_filtered = data[data["Student ID"] == target_student_id]
        if not data_filtered.empty:
            updated_df = data[data["Student ID"] != target_student_id]
            updated_df = updated_df.drop(columns=['Age'])

            conn_gsheet.update(worksheet="sheet1", data=updated_df)
            st.success(f"Student with ID {target_student_id} removed successfully!")
        else:
            st.warning(f"No student found with ID {target_student_id}.")


def filter_search_data(data):
    st.header("Filter/Search Student Data")
    search_term = st.text_input("Search by Student Name or Student ID:")

    if st.button("Search"):
        filtered_data = data[data.apply(lambda row: search_term.lower() in row.astype(str).str.lower().values, axis=1)]
        filtered_data.index += 1
        st.dataframe(filtered_data)

def help():
    option = st.selectbox('Help?', ['--Select--', 'Forgot username', 'Forgot password', 'New register'])

    if option == 'Forgot password':
        try:
            username_of_forgotten_password, email_of_forgotten_password, new_random_password = authenticator.forgot_password()
            if username_of_forgotten_password:
                renew_user_information()
                st.success('New password is {}'.format(new_random_password))
            elif username_of_forgotten_password == False:
                st.error('Username not found')
        except Exception as e:
            st.error(e)

    elif option == 'Forgot username':
        try:
            username_of_forgotten_username, email_of_forgotten_username = authenticator.forgot_username()
            if username_of_forgotten_username:
                st.success('Username is {}'.format(username_of_forgotten_username))
            elif username_of_forgotten_username == False:
                st.error('Email not found')
        except Exception as e:
            st.error(e)

    elif option == 'New register':
        try:
            email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user(pre_authorization=False)
            if email_of_registered_user:
                renew_user_information()
                st.success('User registered successfully')
                st.success(config['credentials'])
        except Exception as e:
            st.error(e)


def admin():
    data = read_data()
    data.index += 1

    with st.container():
        st.title("Student Database Management")
        st.header("Current Student Data")
        data['Student ID'] = data['Student ID'].astype(str)
        data['Phone Number'] = data['Phone Number'].astype(str)
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
        data['Student ID'] = data['Student ID'].astype(str)
        data['Phone Number'] = data['Phone Number'].astype(str)
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
