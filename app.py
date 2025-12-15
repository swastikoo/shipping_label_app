import pandas as pd
import streamlit as st
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph

st.title("📦 Shipping Label Generator (12 per A4 page, auto-fit text)")

uploaded_file = st.file_uploader("Upload Shopify Orders CSV", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df.columns = [c.strip() for c in df.columns]

    required_cols = [
        "Lineitem name",  # contains language in parentheses
        "Shipping Name",
        "Shipping Street",
        "Shipping City",
        "Shipping Zip",
        "Shipping Province",
        "Shipping Phone",
        "Lineitem quantity",
        "Name",  # unique order identifier
    ]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        st.error(f"Missing columns: {', '.join(missing)}")
        st.stop()

    # Forward-fill shipping info per order
    shipping_cols = [
        "Shipping Name",
        "Shipping Street",
        "Shipping City",
        "Shipping Zip",
        "Shipping Province",
        "Shipping Phone",
    ]
    df[shipping_cols] = df.groupby("Name")[shipping_cols].ffill()
    df = df.dropna(subset=shipping_cols)

    # Extract language from Lineitem name
    def extract_language(lineitem_name):
        if "(" in lineitem_name and ")" in lineitem_name:
            return lineitem_name.split("(")[-1].replace(")", "").strip()
        return None

    df["Language"] = df["Lineitem name"].apply(extract_language)
    df = df[df["Language"].notnull()]

    # Build dictionary of orders keyed by shipping info
    orders = {}
    for _, row in df.iterrows():
        phone = str(row["Shipping Phone"]).split(".")[0].strip()
        phone = f"+{phone}" if len(phone) > 10 else f"{phone}"
        zip_code = str(row["Shipping Zip"]).strip().replace("'", "").replace('"', '')
        key = (
            row["Shipping Name"],
            row["Shipping Street"],
            row["Shipping City"],
            zip_code,
            row["Shipping Province"],
            phone,
        )
        if key not in orders:
            orders[key] = {}
        orders[key][row["Language"]] = int(row["Lineitem quantity"])

    # PDF setup
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4

    # Layout specifications
    side_margin = 4 * mm
    top_bottom_margin = 10 * mm
    label_width = 100 * mm
    label_height = 44 * mm
    cols = 2
    rows = 6
    h_spacing = (page_width - 2 * side_margin - cols * label_width) / (cols - 1)
    v_spacing = (page_height - 2 * top_bottom_margin - rows * label_height) / (rows - 1)

    # Base style
    styles = getSampleStyleSheet()
    style = ParagraphStyle(
        'label',
        fontName='Helvetica',
        fontSize=10,
        leading=12,
        wordWrap='CJK'
    )

    # Loop through orders
    for i, (key, lang_quantities) in enumerate(orders.items()):
        shipping_name, street, city, zip_code, province, phone = key
        items_text = ", ".join([f"{lang}: {qty}" for lang, qty in lang_quantities.items()])

        text = (
            f"<font name= 'Helvetica-Bold'>TO:</font><br/>"
            f"<font name= 'Helvetica-Bold'>{shipping_name}</font><br/>"
            f"{street}<br/>"
            f"{city}, {province} {zip_code}<br/>"
            f"{phone}<br/>"
            f"<font name= 'Helvetica-Bold'>Items:</font> {items_text}"
        )

        col = i % cols
        row_num = (i // cols) % rows
        x = side_margin + col * (label_width + h_spacing)
        y = page_height - top_bottom_margin - row_num * (label_height + v_spacing)

        # Dynamic font size to fit inside rectangle with inner padding
        padding = 2 * mm
        max_width = label_width - 2 * padding
        max_height = label_height - 2 * padding
        current_font_size = 10
        style.fontSize = current_font_size
        style.leading = current_font_size + 2

        para = Paragraph(text, style)
        w, h = para.wrap(max_width, max_height)
        while h > max_height and current_font_size > 5:
            current_font_size -= 1
            style.fontSize = current_font_size
            style.leading = current_font_size + 2
            para = Paragraph(text, style)
            w, h = para.wrap(max_width, max_height)

        # Draw paragraph with inner padding
        para.drawOn(c, x + padding, y - h - padding)

        # Draw optional rectangle border for testing alignment
        # c.rect(x, y - label_height, label_width, label_height, stroke=1, fill=0)

        # New page every full sheet
        if (i + 1) % (cols * rows) == 0:
            c.showPage()

    # Finalize last page
    if len(orders) % (cols * rows) != 0:
        c.showPage()

    c.save()
    buffer.seek(0)

    st.success("✅ PDF generated successfully!")
    st.download_button(
        label="⬇️ Download Shipping Labels PDF",
        data=buffer,
        file_name="shipping_labels.pdf",
        mime="application/pdf",
    )








