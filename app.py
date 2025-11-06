import os
import secrets
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash, send_from_directory
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

# -----------------------
# App config
# -----------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET") or secrets.token_urlsafe(24)

# SQLite DB
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///takasmart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Uploads
UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}

# Mail (optional)
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587)) if os.environ.get("MAIL_PORT") else None
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "True") in ("True", "true", "1")
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER") or app.config.get("MAIL_USERNAME")
mail = Mail(app)

# -----------------------
# Models
# -----------------------
class WasteReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    location = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(300))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(50), default="Pending")
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)

    def image_url(self):
        if self.image_filename:
            return url_for("uploaded_file", filename=self.image_filename)
        return url_for("static", filename="placeholder.jpg")

# -----------------------
# Helpers
# -----------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

# -----------------------
# Routes - static uploads
# -----------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# -----------------------
# Routes - pages
# -----------------------
@app.route("/")
def index():
    # counts for chart/hero summary
    total = WasteReport.query.count()
    pending = WasteReport.query.filter_by(status="Pending").count()
    verified = WasteReport.query.filter_by(status="Verified").count()
    collected = WasteReport.query.filter_by(status="Collected").count()
    return render_template("index.html", total=total, pending=pending, verified=verified, collected=collected)

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        # read form
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        location = request.form.get("location")
        description = request.form.get("description")
        latitude = request.form.get("latitude") or None
        longitude = request.form.get("longitude") or None

        # simple validation
        if not name or not email or not location or not description:
            flash("Please fill in all required fields (Name, Email, Location, Description).", "danger")
            return redirect(url_for("report"))

        # image handling
        image = request.files.get("image")
        saved_filename = None
        if image and image.filename != "" and allowed_file(image.filename):
            ext = secure_filename(image.filename).rsplit(".", 1)[1].lower()
            saved_filename = f"{secrets.token_hex(8)}.{ext}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], saved_filename)
            image.save(save_path)

        # convert coords
        try:
            lat = float(latitude) if latitude else None
            lon = float(longitude) if longitude else None
        except ValueError:
            lat = None
            lon = None

        # create record
        rpt = WasteReport(
            name=name, email=email, phone=phone, location=location,
            description=description, image_filename=saved_filename,
            latitude=lat, longitude=lon
        )
        db.session.add(rpt)
        db.session.commit()

        # optional confirmation email to reporter
        if app.config.get("MAIL_USERNAME") and email:
            try:
                msg = Message(
                    subject="TakaSmart — Report Received",
                    recipients=[email],
                    body=f"Hi {name},\n\nThanks — we received your report for {location}. We'll update you when its status changes.\n\nTakaSmart"
                )
                mail.send(msg)
            except Exception as e:
                app.logger.warning("Mail send failed: %s", e)

        flash("Report submitted successfully! Thank you.", "success")
        return redirect(url_for("success"))

    return render_template("report.html")

@app.route("/success")
def success():
    return render_template("success.html")

@app.route("/view")
def view_reports():
    reports = WasteReport.query.order_by(WasteReport.date_reported.desc()).all()
    return render_template("view_reports.html", reports=reports)

@app.route("/admin")
def admin():
    # optional status filter via query param
    s = request.args.get("status")
    if s:
        reports = WasteReport.query.filter_by(status=s).order_by(WasteReport.date_reported.desc()).all()
    else:
        reports = WasteReport.query.order_by(WasteReport.date_reported.desc()).all()
    return render_template("admin.html", reports=reports)

@app.route("/update_status/<int:report_id>", methods=["POST"])
def update_status(report_id):
    new_status = request.form.get("status")
    rpt = WasteReport.query.get_or_404(report_id)
    rpt.status = new_status
    db.session.commit()

    # notify reporter by email if configured
    if app.config.get("MAIL_USERNAME") and rpt.email:
        try:
            msg = Message(
                subject=f"TakaSmart — Report #{rpt.id} status updated",
                recipients=[rpt.email],
                body=f"Hello {rpt.name},\n\nYour report at {rpt.location} is now: {rpt.status}.\n\nThanks,\nTakaSmart"
            )
            mail.send(msg)
        except Exception as e:
            app.logger.warning("Mail send failed: %s", e)

    flash("Report status updated.", "info")
    return redirect(url_for("admin"))

@app.route("/delete/<int:report_id>", methods=["POST"])
def delete_report(report_id):
    rpt = WasteReport.query.get_or_404(report_id)
    # delete image file if exists
    if rpt.image_filename:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], rpt.image_filename))
        except Exception:
            pass
    db.session.delete(rpt)
    db.session.commit()
    flash("Report deleted.", "warning")
    return redirect(url_for("admin"))

# -----------------------
# Start
# -----------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
