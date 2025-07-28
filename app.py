from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
app = Flask(__name__)


load_dotenv() 

ACCOUNT_SID = os.getenv("ACCOUNT_SID")
AUTH_TOKEN = os.getenv("AUTH_TOKEN")
FROM_WHATSAPP = os.getenv("FROM_WHATSAPP")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def write_pending_booking(phone, room, price):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    sheet = gspread.authorize(creds).open("Booking Confirmations").sheet1
    sheet.append_row([phone, room, price, "Pending"])

def confirm_booking(phone):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    sheet = gspread.authorize(creds).open("Booking Confirmations").sheet1
    data = sheet.get_all_records()

    for idx, row in enumerate(data, start=2):  # Start from row 2 (skip header)
        if row["customer"] == phone and row["status"].lower() == "pending":
            sheet.update_cell(idx, 4, "Confirmed ✅")  # 4th column is Status
            return f"✅ Booking confirmed for Room {row['room']} at ₹{row['amount']}/day."

    return "❌ No pending booking found."

# User-initiated: webhook from Twilio
@app.route("/support", methods=['POST','GET'])
def support():
    incoming_msg = request.form.get('Body', '').strip().lower()
    sender = request.form.get('From')
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ['hi', 'hello','hey', 'help', 'support']:
        msg.body("Welcome to hotel Kailash! Write \"food\" for placing order of any delicacy from our kitchen!\n \
                 For any help or support, please contact us at 📞 +91-9810692207.")
    
    elif incoming_msg in ['food', 'menu', 'order']:
        msg.body("""🍽️ Here’s our latest food menu!

        Let us know what you'd like to order.

        Start your message with "order" followed by the items. For example:

        order
        2 x dal makhani
        1 x shahi paneer
        4 x butter naan
        """)
        msg.media("https://hotel-bot.onrender.com/static/1911-restaurant-menu.pdf")

    elif incoming_msg == 'book':
        confirm_booking(sender)
        msg.body("Thanks! Your booking is confirmed")

    return str(resp)


# Manager-initiated: trigger by mobile app
@app.route("/booking", methods=["POST"])
def send_message():
    data = request.get_json()
    to = f"whatsapp:{data['phone']}"
    message = data['message']
    room = data.get("room")
    price = data.get("price")

    write_pending_booking(to, room, price)


    client.messages.create(
        body=message,
        from_=FROM_WHATSAPP,
        to=to
    )
    return {"status": "message sent"}, 200
