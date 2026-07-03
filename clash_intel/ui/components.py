import qrcode
import streamlit as st
from io import BytesIO

@st.cache_data(show_spinner=False)
def generate_upi_qr(upi_url: str) -> bytes:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=2)
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

@st.dialog("Support the Project")
def show_donation_modal():
    st.write("This analytics tool is completely open-source and free to run locally.")

    upi_string = "upi://pay?pa=shrijayant@apl&pn=Victorious%20Clash&cu=INR"
    qr_bytes = generate_upi_qr(upi_string)

    _, col_qr, _ = st.columns([1, 2, 1])
    with col_qr:
        st.image(qr_bytes, caption="Scan via UPI network", use_container_width=True)

    st.divider()
    st.caption(
        "International users: The UPI network currently maps exclusively to domestic Indian banking nodes. "
        "For global alternatives or framework feature requests, contact development coordination directly at: "
        "victorious.onclash@gmail.com"
    )
