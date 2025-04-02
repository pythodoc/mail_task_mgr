import streamlit as st
import psycopg2
import imaplib
import email
from email.header import decode_header
import pandas as pd
from datetime import datetime
import altair as alt

def get_credentials(file_path="config.txt"):
    with open(file_path, "r") as f:
        lines = f.readlines()
        email = lines[0].strip()
        password = lines[1].strip()
    return str(email), str(password)
# 🔧 CONFIGURATION
IMAP_SERVER = "192.168.206.150"
EMAIL_USER, EMAIL_PASS = get_credentials()
# HOTLISTED_DOMAINS = {"greeksoft.co.in", "silverstream.co.in"}
HOTLISTED_DOMAINS={}
DB_CONFIG = {
    "dbname": "ticket_data",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": 5432
}
st.set_page_config(
    page_title="Greeksoft Support Team",
    page_icon="🏂",
    layout="wide",
    initial_sidebar_state="expanded")

alt.themes.enable("dark")

st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)

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

    mail.select("inbox")

    today = datetime.now().strftime("%d-%b-%Y")

    status, messages = mail.search(None, f'SINCE {today}')
    email_ids = messages[0].split()

    conn = get_db_connection()
    cursor = conn.cursor()

    for num in email_ids:
        status, data = mail.fetch(num, "(RFC822)")

        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

        # raw_email = data[0][1]
        # msg = email.message_from_bytes(raw_email)

                sender = msg["From"]
                print(sender)
                message_time=msg["Date"].split()
                print(message_time)
                date=f'{message_time[1]}-{message_time[2]}-{message_time[3]}'
                print(date)
                time=f'{message_time[4]}'
                print(time)
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8")

                sender_domain = sender.split("@")[-1]
                sender_domain = sender_domain.replace('>', '')

                if sender_domain not in HOTLISTED_DOMAINS:
                    cursor.execute('''SELECT MAX("Ticket_No") FROM "Ticket";''')
                    result = cursor.fetchone()

                    if result[0] is None:
                        next_ticket_no = 1
                    else:
                        # Increment the maximum ticket number by 1
                        next_ticket_no = result[0] + 1
                    print(next_ticket_no,date,time,sender, subject, "Pending")
                    cursor.execute('''INSERT INTO "Ticket" ("Ticket_No","Date","Time","From","Subject","Status") VALUES (%s, %s, %s, %s, %s, %s)''',
                                   (next_ticket_no,date,time,sender, subject, "Pending"))
                conn.commit()

    cursor.close()
    conn.close()
    mail.logout()

def check_pending_ticket():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM "Ticket" WHERE "Status"='Pending';''')
    pendings=cursor.fetchall()
    cursor.close()
    conn.close()
    return pendings

def check_resolved_ticket():
    current_date=datetime.now().strftime("%Y-%m-%d")
    print(current_date)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'''SELECT * FROM "Ticket" WHERE "Status"='Resolved' and "Date"='{current_date}';''')
    resolved=cursor.fetchall()
    cursor.close()
    conn.close()
    return resolved


# 📌 Fetch Tickets from Database
def get_tickets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM "Ticket" where "Status"='';''')
    tickets = cursor.fetchall()
    cursor.close()
    conn.close()
    return tickets

# 🔄 Update Ticket Status
def update_ticket(ticket_id, status, assigned_to):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f'''UPDATE "Ticket" SET "Status" = '{status}', "Assigned_to" = '{assigned_to}' WHERE "Ticket_No" = {ticket_id};''')
                   # (str(status), str(assigned_to), int(ticket_id)))
    conn.commit()
    cursor.close()
    conn.close()

# ❌ Delete Ticket
def delete_ticket(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''DELETE FROM "Ticket" WHERE "Ticket"."Ticket_No"=%s''', ((str(ticket_id),)))
    conn.commit()
    cursor.close()
    conn.close()

# 🎨 Streamlit UI

with st.sidebar:
    st.title("📩 Email Ticketing System")
    if st.button("Fetch New Emails"):
        fetch_emails()
        st.sidebar.success("Emails fetched and tickets created!")

    if st.sidebar.button("Check Pending Emails"):
        check_pending_ticket()
        st.success("Pending Tickets fetched!")


col = st.columns((2, 5, 4), gap='medium')
with col[0]:

    st.markdown('#### Pending/Resolved')

    st.metric(label="Pending", value=len(check_pending_ticket()))

    st.metric(label="Resolved",value=len(check_resolved_ticket()))


with col[1]:
    st.markdown('#### All Details')
    tickets = get_tickets()
    df = pd.DataFrame(tickets, columns=["Ticket_No", "Date", "Time", "From", "Subject","Assigned_To",'Status'])
    st.dataframe(df)

    check_pending_ticket()

    pending = check_pending_ticket()
    # print(pending)
    pending_df = pd.DataFrame(pending, columns=["Ticket_No", "Date", "Time", "From", "Subject","Assigned_To",'Status'])
    st.dataframe(pending_df)

    # 🎯 Update Tickets
    st.subheader("🔄 Update Ticket")
    selected_ticket = st.selectbox("Select Ticket to Update", df["Ticket_No"])
    new_status = st.selectbox("Update Status", ["Pending", "Resolved"])
    assignee = st.text_input("Assign To")

    if st.button("Update Ticket"):
        update_ticket(selected_ticket, new_status, assignee)
        st.success("Ticket Updated Successfully!")

    # ❌ Delete Ticket
    st.subheader("❌ Delete Ticket")
    delete_ticket_id = st.selectbox("Select Ticket to Delete", df["Ticket_No"])
    if st.button("Delete Ticket"):
        delete_ticket(delete_ticket_id)
        st.warning("Ticket Deleted!")

with col[2]:
    st.markdown('#### Pending Details')

    pending_df = df[df['Status'] == 'Pending']
    grouped_df = pending_df.groupby('Assigned_To').size().reset_index(name='Pending_Count')
    st.dataframe(grouped_df)





st.sidebar.info("Refresh the page to see the latest changes.")
