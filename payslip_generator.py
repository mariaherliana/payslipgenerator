# Streamlit Payslip Generator
# File: streamlit_payslip_generator.py
# Description: Payslip generator with multiple currencies, OT, allowances, deductions,
# benefits (non-financial), preview and PDF download. Dark blue theme. Ready for
# deployment to Streamlit Cloud.
#
# Instructions to deploy on Streamlit Cloud:
# 1. Create a new app on https://share.streamlit.io and link your repo containing this file.
# 2. Ensure requirements.txt includes: streamlit, reportlab, pillow
# 3. Add this file as app.py or point the cloud app to this file.

import streamlit as st
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from PIL import Image
import base64

st.markdown("""
<style>
/* Streamlit form field labels only */
.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stDateInput label {
    color: #ffffff !important;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# ----------------------- Helper functions -----------------------

def set_page_style():
    st.set_page_config(page_title="Payslip Generator", layout="centered")
    # small CSS for dark-blue theme
    st.markdown(
        """
        <style>
        .reportview-container { background: #0b2336; color: #e6f2fb; }
        .stApp { background: linear-gradient(180deg,#052235 0%, #08344a 100%); color: #e6f2fb; }
        .card { background-color: #062b43; padding: 16px; border-radius: 8px; }
        .muted { color:#bcd6e6 }
        .section-title { color:#dff4ff; font-weight:600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


CURRENCY_SYMBOLS = {
    "IDR": "Rp",
    "SGD": "S$",
    "USD": "$",
    "GBP": "£",
    "EUR": "€",
}

# Format amounts with US or EU numbering style. IDR defaults to no decimals.
def format_amount(value: float, currency: str, number_format: str = "US") -> str:
    try:
        if currency == "IDR":
            # No decimals for IDR
            integer = int(round(value))
            s = f"{integer:,}"
            if number_format == "EU":
                s = s.replace(",", ".")
            return f"{CURRENCY_SYMBOLS[currency]} {s}"
        else:
            s = f"{value:,.2f}"  # 1,234,567.89
            if number_format == "EU":
                # swap comma and dot
                s = s.replace(",", "X").replace(".", ",").replace("X", ".")
            return f"{CURRENCY_SYMBOLS[currency]} {s}"
    except Exception:
        return f"{value}"


def create_payslip_pdf(data: dict, logo_bytes: bytes | None = None) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    def check_page(y):
        if y < 80:
            c.showPage()
            return height - 80
        return y

    # Colors
    header_color = colors.HexColor("#083a5d")
    text_color = colors.black

    # Header block
    c.setFillColor(header_color)
    c.rect(0, height - 80, width, 80, fill=1, stroke=0)

    # Title + Meta
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(120, height - 45, "Payslip")
    c.setFont("Helvetica", 10)
    c.drawString(120, height - 60, f"Date: {data['date']}")
    c.drawRightString(width - 40, height - 45, f"Payslip No: {data['payslip_no']}")

    # Reset to dark text for body
    c.setFillColor(text_color)

    y = height - 110

    # Company Info
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, data['company_name'])
    y -= 14
    c.setFont("Helvetica", 10)
    for line in data['company_address'].split("\n"):
        c.drawString(40, y, line)
        y -= 12
    c.drawString(40, y, f"Phone: {data['company_phone']}")

    # Employee info
    y -= 24
    c.setFont("Helvetica-Bold", 11)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Employee Information")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Name: {data['employee_name']}")
    c.drawString(300, y, f"Employee ID: {data['employee_id']}")
    y -= 14
    c.drawString(40, y, f"Position: {data['position']}")
    c.drawString(300, y, f"Period: {data['period']}")

    # Earnings / Deductions header
    y -= 28
    y = check_page(y)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Earnings")
    c.drawString(300, y, "Amount")
    c.drawString(380, y, "Deductions")
    c.drawString(520, y, "Amount")
    y -= 14

    c.setFont("Helvetica", 10)

    # Base Salary
    c.drawString(40, y, "Base Salary")
    c.drawRightString(360, y, data["fmt_base_salary"])
    if data["deductions"]:
        c.drawString(380, y, data["deductions"][0]["label"])
        c.drawRightString(560, y, data["deductions"][0]["fmt"])
    y -= 14
    y = check_page(y)

    # OT
    c.drawString(40, y, f"Overtime ({data['ot_hours']} hrs @ {data['fmt_ot_rate']}/hr)")
    c.drawRightString(360, y, data["fmt_ot_amount"])
    if len(data["deductions"]) > 1:
        c.drawString(380, y, data["deductions"][1]["label"])
        c.drawRightString(560, y, data["deductions"][1]["fmt"])
    y -= 14
    y = check_page(y)

    # Allowances
    for i, a in enumerate(data["allowances"]):
        c.drawString(40, y, a["label"])
        c.drawRightString(360, y, a["fmt"])
        if len(data["deductions"]) > 2 + i:
            d = data["deductions"][2 + i]
            c.drawString(380, y, d["label"])
            c.drawRightString(560, y, d["fmt"])
        y -= 14
        y = check_page(y)

    # Totals
    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Total Earnings")
    c.drawRightString(360, y, data["fmt_total_earnings"])
    c.drawString(380, y, "Total Deductions")
    c.drawRightString(560, y, data["fmt_total_deductions"])
    y -= 22

    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "Net Pay:")
    c.drawRightString(560, y, data["fmt_net_pay"])
    y -= 30
    y = check_page(y)

    # Employer-paid Benefits
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Employer-Paid Benefits")
    y -= 16
    c.setFont("Helvetica", 10)
    for b in data['benefits']:
        c.drawString(40, y, b['label'])
        c.drawRightString(560, y, b['fmt'])
        y -= 12
        y = check_page(y)

    # END Benefits
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, "Benefits (Non-financial)")
    y -= 16
    c.setFont("Helvetica", 10)

    for b in data["benefits"]:
        c.drawString(40, y, f"- {b}")
        y -= 12
        y = check_page(y)

    # IMPORTANT: remove final c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()

# For compatibility with ReportLab's ImageReader
from reportlab.lib.utils import ImageReader

# ----------------------- Streamlit App -----------------------

set_page_style()

st.title("Payslip Generator")

with st.sidebar:
    st.header("Company Info")
    company_name = st.text_input("Company name", value="My Company Ltd.")
    company_address = st.text_area("Company address", value="123 Business Road
Business City, 12345")
    company_phone = st.text_input("Company phone", value="+1 234 567 890")

    st.header("Settings")
    st.header("Settings")
    currency = st.selectbox("Currency", ["IDR", "SGD", "USD", "GBP", "EUR"], index=2)
    number_format = st.radio("Numbering format", ["US", "EU"], index=0, help="US: 1,234.56 | EU: 1.234,56")
    logo_file = st.file_uploader("Upload company logo (optional)", type=["png", "jpg", "jpeg"])
    next_payslip_no = st.text_input("Starting payslip no.", value=datetime.now().strftime("PSL%Y%m%d-001"))

# Main form
with st.form("payslip_form"):
    st.subheader("Employee details")
    col1, col2 = st.columns(2)
    with col1:
        employee_name = st.text_input("Employee name", value="John Doe")
        employee_id = st.text_input("Employee ID", value="EMP-001")
        position = st.text_input("Position", value="Software Engineer")
    with col2:
        period = st.text_input("Period", value=datetime.now().strftime("%B %Y"))
        payslip_no = st.text_input("Payslip No", value=next_payslip_no)
        date = st.date_input("Date", value=datetime.now())

    st.subheader("Earnings")
    base_salary = st.number_input("Base salary", min_value=0.0, value=3000000.0 if currency=="IDR" else 3000.0, step=1.0)
    st.markdown("**Overtime**")
    ot_hours = st.number_input("OT hours", min_value=0.0, value=0.0, step=0.5)
    ot_rate = st.number_input("OT rate (per hour)", min_value=0.0, value=0.0)

    st.markdown("**Allowances (add as many as needed)**")
    allowances = []
    allow_cnt = st.number_input("Number of allowances", min_value=0, max_value=10, value=1)
    for i in range(allow_cnt):
        label = st.text_input(f"Allowance {i+1} label", value=("Transport" if i==0 else f"Allowance {i+1}"), key=f"al_label_{i}")
        amount = st.number_input(f"Allowance {i+1} amount", min_value=0.0, value=0.0, key=f"al_amount_{i}")
        allowances.append({"label": label, "amount": amount})

    st.subheader("Deductions")
    deductions = []
    ded_cnt = st.number_input("Number of deductions", min_value=0, max_value=10, value=1)
    for i in range(ded_cnt):
        label = st.text_input(f"Deduction {i+1} label", value=("Tax" if i==0 else f"Deduction {i+1}"), key=f"ded_label_{i}")
        amount = st.number_input(f"Deduction {i+1} amount", min_value=0.0, value=0.0, key=f"ded_amount_{i}")
        deductions.append({"label": label, "amount": amount})

    st.subheader("Benefits (employer-paid)")
benefits = []
ben_cnt = st.number_input("Number of benefits", min_value=0, max_value=10, value=1)
for i in range(ben_cnt):
    label = st.text_input(f"Benefit {i+1} label", value=("Health Insurance" if i==0 else f"Benefit {i+1}"), key=f"ben_label_{i}")
    amount = st.number_input(f"Benefit {i+1} amount", min_value=0.0, value=0.0, key=f"ben_amount_{i}")
    benefits.append({"label": label, "amount": amount})

st.form_submit_button("Generate Payslip")("Generate Payslip")

# Perform calculations
ot_amount = ot_hours * ot_rate
total_allowances = sum(a['amount'] for a in allowances)
total_deductions = sum(d['amount'] for d in deductions)
total_earnings = base_salary + ot_amount + total_allowances
net_pay = total_earnings - total_deductions

# Prepare formatted strings
for b in benefits:
    b['fmt'] = format_amount(b['amount'], currency, number_format)
fmt_base_salary = format_amount(base_salary, currency, number_format)
fmt_ot_rate = format_amount(ot_rate, currency, number_format)
fmt_ot_amount = format_amount(ot_amount, currency, number_format)
fmt_total_earnings = format_amount(total_earnings, currency, number_format)
fmt_total_deductions = format_amount(total_deductions, currency, number_format)
fmt_net_pay = format_amount(net_pay, currency, number_format)

for a in allowances:
    a['fmt'] = format_amount(a['amount'], currency, number_format)
for d in deductions:
    d['fmt'] = format_amount(d['amount'], currency, number_format)

# Right column: Preview & PDF
st.markdown("---")
colA, colB = st.columns([1,1])
with colA:
    st.subheader("Preview")
    # Simple HTML preview styled with dark blue theme
    preview_html = f"""
    <div style='background:#062b43;padding:20px;border-radius:8px;color:#e6f2fb'>
      <h2 style='margin:0;color:#dff4ff'>Payslip</h2>
      <p style='margin:4px 0'><strong>{company_name}</strong><br/>{company_address.replace('
','<br/>')}<br/>Phone: {company_phone}</p>
      <p style='margin:4px 0' class='muted'>Payslip No: {payslip_no} &nbsp;&nbsp; Date: {date}</p>
      <hr style='border:0;border-top:1px solid #0b445f' />
      <h4 style='margin-bottom:4px'>Employee</h4>
      <p style='margin:0'>{employee_name} - {employee_id} <br/> {position} | {period}</p>

      <h4 style='margin-top:12px'>Earnings</h4>
      <table style='width:100%'>
        <tr><td>Base Salary</td><td style='text-align:right'>{fmt_base_salary}</td></tr>
        <tr><td>OT ({ot_hours} hrs @ {fmt_ot_rate}/hr)</td><td style='text-align:right'>{fmt_ot_amount}</td></tr>
    """
    for a in allowances:
        preview_html += f"<tr><td>{a['label']}</td><td style='text-align:right'>{a['fmt']}</td></tr>"
    preview_html += f"<tr style='border-top:1px solid #0b445f'><td><strong>Total Earnings</strong></td><td style='text-align:right'><strong>{fmt_total_earnings}</strong></td></tr>"
    preview_html += "</table>"

    preview_html += "<h4 style='margin-top:12px'>Deductions</h4><table style='width:100%'>"
    for d in deductions:
        preview_html += f"<tr><td>{d['label']}</td><td style='text-align:right'>{d['fmt']}</td></tr>"
    preview_html += f"<tr style='border-top:1px solid #0b445f'><td><strong>Total Deductions</strong></td><td style='text-align:right'><strong>{fmt_total_deductions}</strong></td></tr></table>"

    preview_html += f"<h3 style='margin-top:12px'>Net Pay: <span style='float:right'>{fmt_net_pay}</span></h3>"

    preview_html += "<h4 style='margin-top:18px'>Employer-Paid Benefits</h4><table style='width:100%'>"
for b in benefits:
    preview_html += f"<tr><td>{b['label']}</td><td style='text-align:right'>{b['fmt']}</td></tr>"
preview_html += "</table>"</div>"

    st.markdown(preview_html, unsafe_allow_html=True)

with colB:
    st.subheader("Download PDF")
    logo_bytes = None
    if logo_file is not None:
        logo_bytes = logo_file.read()
        try:
            st.image(logo_bytes, width=120)
        except Exception:
            pass

    data = {
        'company_name': company_name,
        'company_address': company_address,
        'company_phone': company_phone,
        'date': date.strftime("%Y-%m-%d"),
        'payslip_no': payslip_no,
        'employee_name': employee_name,
        'employee_id': employee_id,
        'position': position,
        'period': period,
        'base_salary': base_salary,
        'fmt_base_salary': fmt_base_salary,
        'ot_hours': ot_hours,
        'ot_rate': ot_rate,
        'fmt_ot_rate': fmt_ot_rate,
        'ot_amount': ot_amount,
        'fmt_ot_amount': fmt_ot_amount,
        'allowances': allowances,
        'deductions': deductions,
        'benefits': benefits,
        'fmt_total_earnings': fmt_total_earnings,
        'fmt_total_deductions': fmt_total_deductions,
        'fmt_net_pay': fmt_net_pay,
    }

    pdf_bytes = create_payslip_pdf(data, logo_bytes)
    st.download_button("Download Payslip (PDF)", data=pdf_bytes, file_name=f"payslip_{payslip_no}.pdf", mime="application/pdf")

st.caption("Built for Streamlit Cloud — include reportlab and pillow in your requirements.txt")
