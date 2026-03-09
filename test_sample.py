from reportlab.pdfgen import canvas
import os

def ensure_test_pdf():
    filename = "test_sample.pdf"
    
    # Skip if it already exists
    if os.path.exists(filename):
        print(f"✅ {filename} already exists.")
        return

    # Create a basic PDF
    c = canvas.Canvas(filename)
    c.drawString(100, 750, "Studaxis Test Textbook")
    c.drawString(100, 730, "This is a dummy PDF file for testing the local RAG upload endpoint.")
    c.save()
    print(f"✅ Created {filename} successfully.")

if __name__ == "__main__":
    ensure_test_pdf()