import streamlit as st
import psycopg2
import imaplib
import email
from email.header import decode_header
import pandas as pd
from datetime import datetime

def get_credentials(file_path="config.txt"):
    with open(file_path, "r") as f:
        lines = f.readlines()
        email = lines[0].strip()
        password = lines[1].strip()
    return str(email), str(password)
# 🔧 CONFIGURATION
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER, EMAIL_PASS = get_credentials()
HOTLISTED_DOMAINS = {"greeksoft.co.in", "silverstream.co.in"}

DB_CONFIG = {
    "dbname": "ticket_data",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5432
}



# 📌 Database Connection
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

# 📥 Fetch Emails from IMAP
def fetch_emails():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    try:
        mail.login(EMAIL_USER, EMAIL_PASS)
    except imaplib.IMAP4.error as e:
        st.error(f"Login failed: {e}")
        return

    mail.select("Inbox")

    today = datetime.now().strftime("%d-%b-%Y")

    status, messages = mail.search(None, f'SINCE {today}')
    email_ids = messages[0].split()

    conn = get_db_connection()
    cursor = conn.cursor()

    for num in email_ids:
        status, data = mail.fetch(num, "(RFC822)")
        raw_email = data[0][1]
        msg = email.message_from_bytes(raw_email)

        sender = msg["From"]
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")

        sender_domain = sender.split("@")[-1]

        if sender_domain not in HOTLISTED_DOMAINS:
            cursor.execute('''INSERT INTO "Ticket" (Email, Subject, Status) VALUES (%s, %s, %s)''',
                           (sender, subject, "Pending"))
            conn.commit()

    cursor.close()
    conn.close()
    mail.logout()

# 📌 Fetch Tickets from Database
def get_tickets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM "Ticket"''')
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets

# 🔄 Update Ticket Status
def update_ticket(ticket_id, status, assigned_to):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET status=%s, assigned_to=%s WHERE id=%s",
                   (status, assigned_to, ticket_id))
    conn.commit()
    cursor.close()
    conn.close()

# ❌ Delete Ticket
def delete_ticket(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tickets WHERE id=%s", (ticket_id,))
    conn.commit()
    cursor.close()
    conn.close()

# 🎨 Streamlit UI
st.title("📩 Email Ticketing System")

# Sidebar actions
st.sidebar.header("Ticket Actions")
if st.sidebar.button("Fetch New Emails"):
    fetch_emails()
    st.sidebar.success("Emails fetched and tickets created!")

# 📋 Display Tickets
tickets = get_tickets()
df = pd.DataFrame(tickets, columns=["ID", "Email", "Subject", "Status", "Assigned To", "Created At"])
st.dataframe(df)

# 🎯 Update Tickets
st.subheader("Update Ticket")
selected_ticket = st.selectbox("Select Ticket to Update", df["ID"])
new_status = st.selectbox("Update Status", ["Pending", "Done"])
assignee = st.selectbox("Assign To", ["Akash","Nikunj"])

if st.button("Update Ticket"):
    update_ticket(selected_ticket, new_status, assignee)
    st.success("Ticket Updated Successfully!")

# ❌ Delete Ticket
st.subheader("Delete Ticket")
delete_ticket_id = st.selectbox("Select Ticket to Delete", df["ID"])
if st.button("Delete Ticket"):
    delete_ticket(delete_ticket_id)
    st.warning("Ticket Deleted!")

st.sidebar.info("Refresh the page to see the latest changes.")
