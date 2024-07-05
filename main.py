import streamlit as st
import pandas as pd
import datetime
from streamlit_gsheets import GSheetsConnection


conn = st.connection("gsheets", type=GSheetsConnection)

SEX_TYPES = ["Male", "Female", "Others"]

def read_data():
    data = conn.read(worksheet="sheet1", usecols=list(range(6)), ttl=3600)
    return data.dropna(how="all")

def write_data(data):
    conn.write(data)


def main():
    data = read_data()

    st.title("Student Database Management")
    st.header("Current Student Data")
    st.dataframe(data)

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
        data_filtered = data[data["Student ID"] == target_student_id]
        if not data_filtered.empty:
            data = data[data["Student ID"] != target_student_id]
            write_data(data)
            st.success(f"Student with ID {target_student_id} removed successfully!")
        else:
            st.warning(f"No student found with ID {target_student_id}.")


def filter_search_data(data):
    st.header("Filter/Search Student Data")
    search_term = st.text_input("Search by name or student ID:")

    if st.button("Search"):
        filtered_data = data[data.apply(lambda row: search_term.lower() in row.astype(str).str.lower().values, axis=1)]
        st.dataframe(filtered_data)


if __name__ == "__main__":
    main()
