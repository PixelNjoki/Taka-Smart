from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# ---------------------------------------------------
# Flask App Setup
# ---------------------------------------------------
app = Flask(__name__)

app.secret_key = os.environ.get("TAKASMART_SECRET_KEY", "dev_secret_key")

# SQLite Database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///takasmart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Upload Folder Config
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Email Config (you can set these as environment variables)
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("EMAIL_USER")
app.config["MAIL_PASSWORD"] = os.environ.get("EMAIL_PASS")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("EMAIL_USER")

db = SQLAlchemy(app)
mail = Mail(app)

# ---------------------------------------------------
# Database Model
# ---------------------------------------------------
class WasteReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(50), default="Pending")
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------------------------------------------
# Helper Function for File Uploads
# ---------------------------------------------------
def allowed_file(filename):
    allowed_extensions = {"png", "jpg", "jpeg", "gif"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

# ---------------------------------------------------
# Routes
# ---------------------------------------------------
@app.route("/")
def index():
    return render_template('index.html')

def home():
    return render_template("index.html")

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        location = request.form.get("location")
        description = request.form.get("description")
        image = request.files.get("image")

        # Validation
        if not name or not email or not location or not description:
            flash("⚠️ Please fill in all required fields!", "danger")
            return redirect(url_for("report"))

        # Handle Image Upload
        image_path = None
        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(image_path)

        # Save to Database
        new_report = WasteReport(
            name=name,
            email=email,
            phone=phone,
            location=location,
            description=description,
            image_path=image_path,
        )
        db.session.add(new_report)
        db.session.commit()

        # Send Email Notification (optional)
        if email:
            try:
                msg = Message(
                    "Taka Smart Report Submitted",
                    recipients=[email],
                    body=f"Hi {name},\n\nYour waste report at {location} has been successfully submitted.\n\nWe will keep you updated on its progress.\n\nThank you for keeping Kenya clean!\n\n— Taka Smart Team",
                )
                mail.send(msg)
            except Exception as e:
                print("Email not sent:", e)

        flash("✅ Report submitted successfully! Thank you for your contribution.", "success")
        return redirect(url_for("report"))

    return render_template("report.html")

@app.route("/admin")
def admin():
    reports = WasteReport.query.order_by(WasteReport.date_reported.desc()).all()
    return render_template("admin.html", reports=reports)

@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    report = WasteReport.query.get_or_404(id)
    new_status = request.form.get("status")
    report.status = new_status
    db.session.commit()

    # Notify user via email
    if report.email:
        try:
            msg = Message(
                "Taka Smart Report Status Update",
                recipients=[report.email],
                body=f"Hi {report.name},\n\nYour report status has been updated to: {report.status}.\n\nThank you for using Taka Smart!",
            )
            mail.send(msg)
        except Exception as e:
            print("Email not sent:", e)

    flash("🔄 Report status updated successfully!", "info")
    return redirect(url_for("admin"))

@app.route("/delete/<int:id>")
def delete(id):
    report = WasteReport.query.get_or_404(id)
    db.session.delete(report)
    db.session.commit()
    flash("🗑️ Report deleted successfully!", "warning")
    return redirect(url_for("admin"))

# ---------------------------------------------------
# Run the App
# ---------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
