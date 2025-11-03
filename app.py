from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# -----------------------------------
# Flask App Setup
# -----------------------------------
app = Flask(__name__)

# Don't hardcode secret keys; load from the environment in production, otherwise generate
# a secure random key for development/testing.
import os
import secrets
app.secret_key = os.environ.get("TAKASMART_SECRET_KEY") or secrets.token_urlsafe(32)

# Database setup (SQLite)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///takasmart.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# -----------------------------------
# Database Model
# -----------------------------------
class WasteReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float)      # 🆕 Added
    longitude = db.Column(db.Float)     # 🆕 Added
    status = db.Column(db.String(50), default="Pending")
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)

# -----------------------------------
# Routes
# -----------------------------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        location = request.form.get("location")
        description = request.form.get("description")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")

        if not name or not location or not description:
            flash("Please fill in all required fields!", "danger")
            return redirect(url_for("report"))
        
        # convert lat/lon to float when present
        try:
            lat = float(latitude) if latitude else None
            lon = float(longitude) if longitude else None
        except ValueError:
            lat = None
            lon = None

        new_report = WasteReport(
            name=name,
            email=email,
            location=location,
            description=description,
            latitude=lat,
            longitude=lon
        )
        db.session.add(new_report)
        db.session.commit()
        flash("Your report has been submitted successfully!", "success")
        return redirect(url_for("home"))

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
    flash("Report status updated successfully!", "info")
    return redirect(url_for("admin"))

@app.route("/delete/<int:id>")
def delete(id):
    report = WasteReport.query.get_or_404(id)
    db.session.delete(report)
    db.session.commit()
    flash("Report deleted successfully!", "warning")
    return redirect(url_for("admin"))

# -----------------------------------
# Run the App
# -----------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
