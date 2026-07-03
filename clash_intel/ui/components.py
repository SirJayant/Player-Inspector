import qrcode
import streamlit as st
from io import BytesIO

@st.cache_data(show_spinner=False)
def get_upi_qr_bytes(upi_url: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()

@st.dialog("⚡ Fund the Elixir Pipeline")
def show_donation_modal():
    st.caption("Keep the API scraping engine running securely with 0% middleman fees.")

    upi_string = "upi://pay?pa=shrijayant@apl&pn=Victorious%20Clash&cu=INR"
    qr_bytes = get_upi_qr_bytes(upi_string)

    _, col_qr, _ = st.columns([1, 2, 1])
    with col_qr:
        st.image(qr_bytes, caption="Scan via any UPI app", use_container_width=True)

    st.divider()

    st.markdown(
        "**🌍 Not from India?**\n\n"
        "Since the global banking system is a bureaucratic nightmare, I literally cannot accept international cards right now without sacrificing my firstborn to regulatory fees. So, this QR code only works for the Indian UPI network.\n\n"
        "If you are a high-roller from overseas and absolutely *must* throw money at me to keep my hobby alive, drop an email to **victorious.onclash@gmail.com** and we'll figure out a dark elixir trade."
    )
