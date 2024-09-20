import streamlit as st
import smtplib
from email.message import EmailMessage
from simple_salesforce import Salesforce, SalesforceLogin
import os
from datetime import datetime, timedelta
import random

# Salesforce credentials
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN")
SF_DOMAIN = 'test'

# Connect to Salesforce
try:
    session_id, instance = SalesforceLogin(
        username=SF_USERNAME, 
        password=SF_PASSWORD, 
        security_token=SF_SECURITY_TOKEN, 
        domain=SF_DOMAIN
    )
    sf = Salesforce(session_id=session_id, instance=instance)
    st.success("Connected to Salesforce successfully!")
except Exception as e:
    st.error(f"Failed to connect to Salesforce: {e}")

# Email and contact details
ADMIN_EMAIL = "jaevkim@gmail.com"
SENDER_EMAIL = "perrequestform@gmail.com"
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")  # Replace with your App Password
CONTACT_ID = "003ca000003iJh6AAE"  # Contact ID for the admin where secret word will be stored

# Function to generate a random secret word
def generate_secret_word():
    words = ["apple", "bird", "cat", "dog", "elephant", "fish", "grape", "hat", "ice", "jungle", "kite", "lemon", "moon", "nest", "orange", "penguin", "queen", "rain", "sun", "tree", "umbrella", "vase", "wind", "xylophone", "yarn", "zebra"]
    return ''.join(random.sample(words, 3))

# Function to retrieve the secret word and last changed date from Salesforce
def load_secret_word():
    try:
        contact = sf.Contact.get(CONTACT_ID)
        secret_word = contact.get('PER_Form_Secret_Word__c')
        last_changed_date = contact.get('PER_Form_Secret_Changed_Date__c')  # Fetch the custom field
        return secret_word, last_changed_date
    except Exception as e:
        st.error(f"Failed to load secret word from Salesforce: {e}")
        return None, None

# Function to safely parse the datetime from Salesforce, which may or may not include microseconds
def parse_salesforce_datetime(last_changed):
    try:
        # Try parsing with microseconds
        return datetime.strptime(last_changed, '%Y-%m-%dT%H:%M:%S.%fZ')
    except ValueError:
        # If that fails, try without microseconds
        return datetime.strptime(last_changed.split('.')[0] + 'Z', '%Y-%m-%dT%H:%M:%SZ')

# Function to save the secret word and update the last changed date in Salesforce
def save_secret_word(secret_word):
    try:
        sf.Contact.update(CONTACT_ID, {
            'PER_Form_Secret_Word__c': secret_word,
            'PER_Form_Secret_Changed_Date__c': datetime.now().isoformat()  # Save current date/time
        })
    except Exception as e:
        st.error(f"Failed to save secret word to Salesforce: {e}")

# Function to send email notification to the administrator
def send_email(new_secret_word):
    # Create email message object
    message = EmailMessage()
    message.set_content(f"The new secret word is: {new_secret_word}")
    message['Subject'] = 'Secret Word Updated'
    message['From'] = SENDER_EMAIL
    message['To'] = ADMIN_EMAIL

    # SMTP server details
    smtp_server = 'smtp.gmail.com'
    smtp_port = 465  # SMTP SSL port number
    smtp_email = SENDER_EMAIL
    smtp_password = os.getenv("SENDER_PASSWORD")  # Using environment variable for security

    # Send the email
    try:
        # Create an SMTP SSL connection
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_email, smtp_password)
            server.send_message(message)
            st.success("Email sent successfully!")
    except Exception as e:
        st.error(f"Failed to send email. Error: {str(e)}")

# Load current secret word and the last changed date from Salesforce
current_secret_word, last_changed = load_secret_word()

# If it's the first run or more than 3 months have passed, generate a new secret word
if not current_secret_word or last_changed is None or (datetime.now() - parse_salesforce_datetime(last_changed) > timedelta(days=90)):
    new_secret_word = generate_secret_word()
    save_secret_word(new_secret_word)  # Save new secret word in Salesforce and update last changed date
    send_email(new_secret_word)  # Notify admin via email
    current_secret_word = new_secret_word
    st.info(f"A new secret word has been generated and saved in Salesforce.")
else:
    st.info(f"Current secret word is still valid. Last changed on {last_changed[:10]}")

# Prompt for the secret word
secret_input = st.text_input("Enter the secret word to access the form:", type="password")

# Check if the secret word is correct
if secret_input == current_secret_word:
    st.success("Secret word accepted! You may proceed with the form.")
    
    # Display the form with the specified fields
    with st.form(key='request_form'):
        first_name = st.text_input("First Name")
        middle_name = st.text_input("Middle Name")
        last_name = st.text_input("Last Name")
        preferred_email = st.text_input("Preferred Email Address")
        job_title = st.text_input("Job Title")
        practice_name = st.text_input("Practice Name")
        practice_address = st.text_input("Practice Address")
        supervisor_name = st.text_input("Supervisor Full Name")
        reasoning = st.text_area("Reasoning behind Request")
        
        # Modified question with radio buttons for Yes/No
        has_urmc_account = st.radio(
            "Already have URMC account for eRecords or prior engagement?",
            options=["Yes", "No"]
        )

        # Submit button
        submit_button = st.form_submit_button(label='Submit')

        if submit_button:
            try:
                # Query to find the Contact ID based on First Name and Last Name
                contact_query = f"SELECT Id, AccountId FROM Contact WHERE FirstName = '{first_name}' AND LastName = '{last_name}' LIMIT 1"
                contact_result = sf.query(contact_query)

                # Initialize ContactId and AccountId as None
                contact_id = None
                account_id = None

                # Check if a matching contact is found
                if contact_result['totalSize'] > 0:
                    contact_id = contact_result['records'][0]['Id']
                    account_id = contact_result['records'][0]['AccountId']
                    
                # Create a dictionary with the Case fields
                case_data = {
                    'RecordTypeId': '012Dn000000FGWvIAO',
                    'Team__c': 'Information Services',
                    'Case_Type__c': 'System Access Request',
                    'Case_Type_Specific__c': 'PER',
                    'Estimated_Start_Date__c': datetime.now().date().isoformat(),
                    'System__c': 'PER',
                    'Severity__c': 'Individual',
                    'Effort__c': 'Low',
                    'Status': 'New',
                    'Priority': 'Medium',
                    'Reason': 'New problem',
                    'Origin': 'Email',
                    'Subject': f"{first_name} {last_name} PER Request Form",
                    'Description': (
                        f"First Name: {first_name}\n"
                        f"Middle Name: {middle_name}\n"
                        f"Last Name: {last_name}\n"
                        f"Preferred Email Address: {preferred_email}\n"
                        f"Job Title: {job_title}\n"
                        f"Practice Name: {practice_name}\n"
                        f"Practice Address: {practice_address}\n"
                        f"Supervisor Full Name: {supervisor_name}\n"
                        f"Reasoning behind Request: {reasoning}\n"
                        f"Already have URMC account: {has_urmc_account}"
                    )
                }

                # Add ContactId and AccountId to case_data only if they are not None
                if contact_id:
                    case_data['ContactId'] = contact_id
                if account_id:
                    case_data['AccountId'] = account_id

                # Create the Case object in Salesforce
                case = sf.Case.create(case_data)
                
                st.success("Form submitted successfully and Case created in Salesforce!")
                # Display submitted data for review
                st.write("Here's what you've submitted:")
                st.write({
                    "First Name": first_name,
                    "Middle Name": middle_name,
                    "Last Name": last_name,
                    "Preferred Email Address": preferred_email,
                    "Job Title": job_title,
                    "Practice Name": practice_name,
                    "Practice Address": practice_address,
                    "Supervisor Full Name": supervisor_name,
                    "Reasoning behind Request": reasoning,
                    "Has URMC account": has_urmc_account
                })
            except Exception as e:
                st.error(f"Failed to create Case in Salesforce: {e}")

else:
    if secret_input:
        st.error("Incorrect secret word. Please try again.")
