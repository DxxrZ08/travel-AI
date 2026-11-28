"""
🌍 AI Travel Planner — Flask Web Application
Production-ready travel planning app with authentication, database, and AI integration.
"""

import os
import uuid
import secrets
import hmac
import re
from html import escape
from html.parser import HTMLParser
import markdown
import click
from datetime import datetime, timezone
from functools import wraps
from urllib.parse import urlsplit

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, session, abort,
)
from flask_login import (
    LoginManager, login_user, logout_user,
    login_required, current_user,
)
from sqlalchemy import inspect, text

from config import config
from models import db, User, Destination, Trip, Review, ChatMessage, PointOfInterest
from travel_ai import get_ai_client, get_ai_response, build_travel_prompt, build_budget_prompt, chat_response
from firebase_auth import verify_firebase_token, get_firebase_client_config, is_firebase_configured


def admin_required(view):
    """Allow access only to authenticated administrator accounts."""
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


def safe_next_url(target):
    """Accept only relative same-site redirect targets."""
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/") or target.startswith("//"):
        return None
    return target


URL_EDGE_CHARS = "".join(chr(code) for code in range(0x21))


def normalize_url_value(value):
    normalized = value.strip().strip(URL_EDGE_CHARS)
    if any(ord(character) < 0x20 for character in normalized):
        return None
    return normalized


class SafeMarkdownHTML(HTMLParser):
    """Keep Markdown formatting while removing raw HTML and unsafe links."""
    ALLOWED_TAGS = {"p", "br", "hr", "strong", "em", "b", "i", "del", "blockquote", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "code", "table", "thead", "tbody", "tr", "th", "td", "a", "img"}
    VOID_TAGS = {"br", "hr", "img"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.ALLOWED_TAGS:
            return
        safe_attrs = []
        seen_attributes = set()
        for name, value in attrs:
            if name in seen_attributes:
                continue
            seen_attributes.add(name)
            if value is None:
                continue
            if name in {"title", "alt"}:
                safe_attrs.append(f' {name}="{escape(value, quote=True)}"')
            elif name == "href" and tag == "a":
                normalized_value = normalize_url_value(value)
                if normalized_value is None:
                    continue
                try:
                    parsed = urlsplit(normalized_value)
                except ValueError:
                    continue
                if parsed.scheme.lower() in {"", "http", "https", "mailto"} and not normalized_value.startswith("//"):
                    safe_attrs.append(f' href="{escape(normalized_value, quote=True)}"')
            elif name == "src" and tag == "img":
                normalized_value = normalize_url_value(value)
                if normalized_value is None:
                    continue
                try:
                    parsed = urlsplit(normalized_value)
                except ValueError:
                    continue
                if parsed.scheme.lower() in {"http", "https"} or (not parsed.scheme and normalized_value and not normalized_value.startswith("//")):
                    safe_attrs.append(f' src="{escape(normalized_value, quote=True)}"')
        self.parts.append(f"<{tag}{''.join(safe_attrs)}>")

    def handle_endtag(self, tag):
        if tag in self.ALLOWED_TAGS and tag not in self.VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data):
        self.parts.append(escape(data))

    def sanitized_html(self):
        return "".join(self.parts)


def sanitize_markdown_html(rendered_html):
    # Escape bare ampersands before HTMLParser decodes semicolonless entities in URLs.
    rendered_html = re.sub(
        r"&(?!#(?:[0-9]+|[xX][0-9a-fA-F]+);|[A-Za-z][A-Za-z0-9]+;)",
        "&amp;",
        rendered_html,
    )
    sanitizer = SafeMarkdownHTML()
    sanitizer.feed(rendered_html)
    sanitizer.close()
    return sanitizer.sanitized_html()

# ── App Factory ──────────────────────────────────────────────────────────────
def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV") or ("production" if os.getenv("VERCEL") else "default")

    app = Flask(__name__, static_folder="public/static", static_url_path="/static")
    app.config.from_object(config[config_name])
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured for every application worker")

    def csrf_token():
        token = session.get("csrf_token")
        if not token:
            token = secrets.token_urlsafe(32)
            session["csrf_token"] = token
        return token

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_from_csrf():
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return None
        supplied = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        stored = session.get("csrf_token")
        if not stored or not supplied or not hmac.compare_digest(supplied, stored):
            abort(400)
        return None

    # Initialize extensions
    db.init_app(app)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Markdown filter
    @app.template_filter("md")
    def markdown_filter(text):
        if not text:
            return ""
        rendered = markdown.markdown(str(text), extensions=["tables", "fenced_code", "nl2br"])
        return sanitize_markdown_html(rendered)

    # Create tables
    with app.app_context():
        db.create_all()
        user_columns = {column["name"] for column in inspect(db.engine).get_columns("users")}
        if "role" not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'"))
        if "firebase_uid" not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN firebase_uid VARCHAR(128)"))
        if "avatar_url" not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500) DEFAULT ''"))
        if "auth_provider" not in user_columns:
            with db.engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'"))
        if Destination.query.count() == 0:
            try:
                from seed_destinations import seed_database
                seed_database(app)
            except Exception:
                db.session.add_all([
                    Destination(
                        name="Kyoto",
                        city="Kyoto",
                        country="Japan",
                        category="Cultural",
                        description="Temple paths, traditional streets, and quiet gardens make Kyoto a rewarding city to explore at a slower pace.",
                        rating=4.9,
                        review_count=328,
                        best_time="March to May, October to November",
                        avg_cost_per_day=145,
                        currency="USD",
                        image_url="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=1000&auto=format&fit=crop&q=85",
                        highlights="Fushimi Inari Shrine, Arashiyama, Nishiki Market",
                        is_featured=True,
                    ),
                    Destination(
                        name="Amalfi Coast",
                        city="Positano",
                        country="Italy",
                        category="Coastal",
                        description="Colorful cliffside villages, coastal walks, and long lunches define this sunlit stretch of southern Italy.",
                        rating=4.8,
                        review_count=241,
                        best_time="May to June, September",
                        avg_cost_per_day=210,
                        currency="USD",
                        image_url="https://images.unsplash.com/photo-1533587851505-d119e13fa0d7?w=1000&auto=format&fit=crop&q=85",
                        highlights="Positano, Ravello, Path of the Gods",
                        is_featured=True,
                    ),
                    Destination(
                        name="Machu Picchu",
                        city="Cusco Region",
                        country="Peru",
                        category="Adventure",
                        description="Trace Inca history through mountain scenery, archaeological sites, and the lively streets of nearby Cusco.",
                        rating=4.9,
                        review_count=196,
                        best_time="May to September",
                        avg_cost_per_day=95,
                        currency="USD",
                        image_url="https://images.unsplash.com/photo-1526392060635-9d6019884377?w=1000&auto=format&fit=crop&q=85",
                        highlights="Machu Picchu, Sacred Valley, Cusco",
                        is_featured=True,
                    ),
                    Destination(
                        name="Marrakech",
                        city="Marrakech",
                        country="Morocco",
                        category="Cultural",
                        description="A sensory city of tiled courtyards, busy souks, garden hideaways, and memorable Moroccan food.",
                        rating=4.7,
                        review_count=174,
                        best_time="March to May, September to November",
                        avg_cost_per_day=80,
                        currency="USD",
                        image_url="https://images.unsplash.com/photo-1597212618440-806262de4f6b?w=1000&auto=format&fit=crop&q=85",
                        highlights="Jemaa el-Fnaa, Bahia Palace, Majorelle Garden",
                        is_featured=True,
                    ),
                    Destination(
                        name="Banff National Park",
                        city="Banff",
                        state="Alberta",
                        country="Canada",
                        category="Nature",
                        description="Turquoise alpine lakes, mountain trails, and wildlife make Banff a classic base for the Canadian Rockies.",
                        rating=4.9,
                        review_count=212,
                        best_time="June to September",
                        avg_cost_per_day=175,
                        currency="USD",
                        image_url="/static/images/destination-placeholder.svg",
                        highlights="Lake Louise, Moraine Lake, Icefields Parkway",
                        is_featured=True,
                    ),
                    Destination(
                        name="Lisbon",
                        city="Lisbon",
                        country="Portugal",
                        category="City",
                        description="Ride historic trams between hilltop viewpoints, neighborhood cafes, and the waterfront districts of Portugal's capital.",
                        rating=4.8,
                        review_count=289,
                        best_time="April to June, September to October",
                        avg_cost_per_day=120,
                        currency="USD",
                        image_url="https://images.unsplash.com/photo-1555881400-74d7acaacd8b?w=1000&auto=format&fit=crop&q=85",
                        highlights="Alfama, Belém, Miradouro da Senhora do Monte",
                        is_featured=True,
                    ),
                ])
                db.session.commit()

        try:
            from seed_destinations import refresh_destination_images
            refresh_destination_images()
        except Exception:
            # Keep startup logs free of database URLs and other connection details.
            app.logger.warning("Destination image refresh could not be completed.")

        for destination in Destination.query.filter(
            Destination.image_url.contains("photo-1503614472-8c93d56cd938")
        ).all():
            destination.image_url = "/static/images/destination-placeholder.svg"
        db.session.commit()

    @app.cli.command("create-admin")
    def create_admin():
        """Create an administrator or promote an existing account."""
        email = click.prompt("Admin email").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            user.role = "admin"
            db.session.commit()
            click.echo(f"Administrator access enabled for {user.email}.")
            return

        username = click.prompt("Username")
        full_name = click.prompt("Full name", default="")
        password = click.prompt("Password", hide_input=True, confirmation_prompt=True)
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        if User.query.filter_by(username=username).first():
            raise click.ClickException("That username is already in use.")

        user = User(username=username, email=email, full_name=full_name, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator account created for {email}.")

    @app.cli.command("seed-destinations")
    def seed_destinations_command():
        """Seed destinations from data/ into database."""
        from seed_destinations import seed_database
        seed_database()
        click.echo("Destinations seeded successfully!")

    # ── Context Processor ────────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        return {
            "now": datetime.now(timezone.utc),
            "firebase_config": get_firebase_client_config(),
            "is_firebase_configured": is_firebase_configured(),
        }

    # ── PUBLIC ROUTES ────────────────────────────────────────────────────

    @app.route("/")
    def index():
        """Landing page."""
        featured = Destination.query.filter_by(is_featured=True).limit(6).all()
        top_rated = Destination.query.order_by(Destination.rating.desc()).limit(8).all()
        total_destinations = Destination.query.count()
        total_users = User.query.count()
        total_trips = Trip.query.count()
        return render_template(
            "index.html",
            featured=featured,
            top_rated=top_rated,
            stats={"destinations": total_destinations, "users": total_users, "trips": total_trips},
        )

    # ── AUTH ROUTES ──────────────────────────────────────────────────────

    @app.route("/api/firebase-config")
    def api_firebase_config():
        """Expose client Firebase config."""
        return jsonify(get_firebase_client_config())

    @app.route("/verify-token", methods=["POST"])
    @app.route("/api/auth/firebase-login", methods=["POST"])
    def firebase_login():
        """Authenticate user using Firebase ID token (e.g. Google Sign-In or Firebase Auth)."""
        data = request.get_json(silent=True) or {}
        id_token = data.get("idToken") or data.get("id_token")
        if not id_token:
            return jsonify({"error": "Missing Firebase ID token"}), 400

        decoded = verify_firebase_token(id_token)
        if not decoded:
            return jsonify({"error": "Invalid or expired Firebase token"}), 401

        uid = decoded.get("uid")
        email = (decoded.get("email") or "").strip().lower()
        if not uid or not email or decoded.get("email_verified") is not True:
            return jsonify({"error": "A verified Firebase email is required to sign in"}), 403

        user = User.query.filter_by(firebase_uid=uid).first()
        if not user:
            user = User.query.filter_by(email=email).first()

        firebase_info = decoded.get("firebase") or {}
        sign_in_provider = str(firebase_info.get("sign_in_provider", "")).lower()
        provider_name = "google" if "google" in sign_in_provider else "firebase"
        name = (decoded.get("name") or "").strip()
        picture = (decoded.get("picture") or "").strip()

        if user:
            user.firebase_uid = uid
            if picture and not user.avatar_url:
                user.avatar_url = picture
            if name and not user.full_name:
                user.full_name = name
            if user.auth_provider == "local":
                user.auth_provider = provider_name
            db.session.commit()
        else:
            base_username = (email.split("@")[0] if email else "traveler").replace(".", "_")[:20]
            username = base_username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User(
                username=username,
                email=email,
                full_name=name or username,
                firebase_uid=uid,
                avatar_url=picture,
                auth_provider=provider_name,
                role="user",
            )
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            db.session.commit()

        login_user(user, remember=True)
        flash(f"Welcome, {user.full_name or user.username}! ✨ Signed in successfully.", "success")
        next_target = safe_next_url(data.get("next") or request.args.get("next"))
        redirect_url = next_target or url_for("admin_dashboard" if user.is_admin else "dashboard")
        return jsonify({
            "success": True,
            "redirect": redirect_url,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
            }
        })

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """User registration."""
        if current_user.is_authenticated:
            return redirect(url_for("admin_dashboard" if current_user.is_admin else "dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            full_name = request.form.get("full_name", "").strip()

            # Validation
            errors = []
            if len(username) < 3:
                errors.append("Username must be at least 3 characters.")
            if "@" not in email:
                errors.append("Please enter a valid email.")
            if password != confirm:
                errors.append("Passwords do not match.")
            if User.query.filter_by(username=username).first():
                errors.append("Username already taken.")
            if User.query.filter_by(email=email).first():
                errors.append("Email already registered.")

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("register.html")

            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template("register.html")

            user = User(username=username, email=email, full_name=full_name, role="user")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            login_user(user)
            flash("Welcome aboard! 🎉 Your account has been created.", "success")
            return redirect(url_for("dashboard"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """User login."""
        if current_user.is_authenticated:
            return redirect(url_for("admin_dashboard" if current_user.is_admin else "dashboard"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            user = User.query.filter(
                (User.username == username) | (User.email == username)
            ).first()

            if user and user.check_password(password):
                login_user(user, remember=request.form.get("remember"))
                flash(f"Welcome back, {user.full_name or user.username}! 👋", "success")
                next_page = safe_next_url(request.args.get("next"))
                default_page = "admin_dashboard" if user.is_admin else "dashboard"
                return redirect(next_page or url_for(default_page))
            else:
                flash("Invalid username or password.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        """User logout."""
        logout_user()
        flash("You've been logged out. See you soon! 👋", "info")
        return redirect(url_for("index"))

    # ── DASHBOARD ────────────────────────────────────────────────────────

    @app.route("/dashboard")
    @login_required
    def dashboard():
        """User dashboard."""
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        recent_trips = current_user.trips.order_by(Trip.created_at.desc()).limit(5).all()
        trip_count = current_user.trips.count()
        review_count = current_user.reviews.count()
        featured = (
            Destination.query.filter_by(is_featured=True)
            .order_by(Destination.rating.desc())
            .limit(8)
            .all()
        )
        if len(featured) < 8:
            featured_ids = [destination.id for destination in featured]
            extra_query = Destination.query
            if featured_ids:
                extra_query = extra_query.filter(~Destination.id.in_(featured_ids))
            featured.extend(extra_query.order_by(Destination.rating.desc()).limit(8 - len(featured)).all())
        return render_template(
            "dashboard.html",
            recent_trips=recent_trips,
            trip_count=trip_count,
            review_count=review_count,
            featured=featured,
        )

    @app.route("/admin")
    @admin_required
    def admin_dashboard():
        """Administrator overview and account-management entry point."""
        return render_template(
            "admin_dashboard.html",
            user_count=User.query.filter_by(role="user").count(),
            admin_count=User.query.filter_by(role="admin").count(),
            destination_count=Destination.query.count(),
            trip_count=Trip.query.count(),
            recent_users=User.query.order_by(User.created_at.desc()).limit(8).all(),
        )

    @app.route("/admin/users")
    @admin_required
    def admin_users():
        """Search and filter registered accounts for administrators."""
        search = request.args.get("search", "").strip()
        role = request.args.get("role", "all")
        query = User.query
        if search:
            query = query.filter(
                (User.username.ilike(f"%{search}%"))
                | (User.email.ilike(f"%{search}%"))
                | (User.full_name.ilike(f"%{search}%"))
            )
        if role in {"user", "admin"}:
            query = query.filter_by(role=role)
        users = query.order_by(User.created_at.desc()).all()
        return render_template("admin_users.html", users=users, search=search, role=role)

    # ── DESTINATIONS ─────────────────────────────────────────────────────

    @app.route("/destinations")
    def destinations():
        """Browse all destinations with search & filter."""
        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "")
        country = request.args.get("country", "")
        sort = request.args.get("sort", "rating")

        query = Destination.query

        if search:
            query = query.filter(
                (Destination.name.ilike(f"%{search}%")) |
                (Destination.city.ilike(f"%{search}%")) |
                (Destination.country.ilike(f"%{search}%")) |
                (Destination.description.ilike(f"%{search}%"))
            )
        if category:
            query = query.filter_by(category=category)
        if country:
            query = query.filter_by(country=country)

        if sort == "rating":
            query = query.order_by(Destination.rating.desc())
        elif sort == "cost_low":
            query = query.order_by(Destination.avg_cost_per_day.asc())
        elif sort == "cost_high":
            query = query.order_by(Destination.avg_cost_per_day.desc())
        elif sort == "name":
            query = query.order_by(Destination.name.asc())

        pagination = query.paginate(page=page, per_page=12, error_out=False)

        # Get unique categories and countries for filters
        categories = db.session.query(Destination.category).distinct().order_by(Destination.category).all()
        countries = db.session.query(Destination.country).distinct().order_by(Destination.country).all()

        return render_template(
            "destinations.html",
            destinations=pagination.items,
            pagination=pagination,
            categories=[c[0] for c in categories if c[0]],
            countries=[c[0] for c in countries if c[0]],
            search=search,
            category=category,
            country=country,
            sort=sort,
        )

    @app.route("/destination/<int:dest_id>")
    def destination_detail(dest_id):
        """Single destination detail page."""
        dest = Destination.query.get_or_404(dest_id)
        reviews = dest.reviews.order_by(Review.created_at.desc()).all()
        user_reviewed = False
        if current_user.is_authenticated:
            user_reviewed = Review.query.filter_by(
                user_id=current_user.id, destination_id=dest_id
            ).first() is not None
        pois = dest.pois.order_by(PointOfInterest.stars.desc()).limit(18).all()
        return render_template(
            "destination_detail.html",
            destination=dest,
            reviews=reviews,
            user_reviewed=user_reviewed,
            pois=pois,
        )

    @app.route("/destination/<int:dest_id>/review", methods=["POST"])
    @login_required
    def add_review(dest_id):
        """Add a review to a destination."""
        dest = Destination.query.get_or_404(dest_id)

        existing = Review.query.filter_by(user_id=current_user.id, destination_id=dest_id).first()
        if existing:
            flash("You've already reviewed this destination.", "warning")
            return redirect(url_for("destination_detail", dest_id=dest_id))

        rating = request.form.get("rating", 5, type=float)
        title = request.form.get("title", "").strip()
        comment = request.form.get("comment", "").strip()

        review = Review(
            user_id=current_user.id,
            destination_id=dest_id,
            rating=min(max(rating, 1), 5),
            title=title,
            comment=comment,
        )
        db.session.add(review)

        # Update destination rating
        all_reviews = dest.reviews.all() + [review]
        dest.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1)
        dest.review_count = len(all_reviews)
        db.session.commit()

        flash("Thanks for your review! ⭐", "success")
        return redirect(url_for("destination_detail", dest_id=dest_id))

    # ── TRIP PLANNING ────────────────────────────────────────────────────

    @app.route("/plan", methods=["GET", "POST"])
    @login_required
    def plan_trip():
        """AI-powered trip planning page."""
        suggested_destinations = (
            Destination.query.order_by(
                Destination.is_featured.desc(),
                Destination.rating.desc(),
                Destination.name.asc(),
            )
            .limit(12)
            .all()
        )
        top_destinations = [
            f"{destination.name}, {destination.country}".strip(", ")
            if destination.country
            else destination.name
            for destination in suggested_destinations
        ]

        if request.method == "POST":
            destination = request.form.get("destination", "").strip()
            duration = request.form.get("duration", 5, type=int)
            budget = request.form.get("budget", "Mid-Range")
            travelers = request.form.get("travelers", 1, type=int)
            travel_style = request.form.get("travel_style", "Balanced Mix")
            interests = request.form.getlist("interests")
            start_date = request.form.get("start_date", "")
            special_requests = request.form.get("special_requests", "").strip()

            if not destination:
                flash("Please enter a destination!", "warning")
                return render_template(
                    "plan_trip.html",
                    top_destinations=top_destinations,
                    suggested_destinations=suggested_destinations,
                )

            # Build prompt and get AI response
            api_key = app.config["NVIDIA_API_KEY"]
            if not api_key:
                flash("NVIDIA API key not configured. Please contact admin.", "danger")
                return render_template(
                    "plan_trip.html",
                    top_destinations=top_destinations,
                    suggested_destinations=suggested_destinations,
                )

            try:
                client = get_ai_client(api_key)

                # Look up real POIs for this destination to inject as hints
                poi_hints = None
                dest_match = Destination.query.filter(
                    Destination.name.ilike(f"%{destination}%")
                ).first()
                if dest_match:
                    pois = PointOfInterest.query.filter_by(
                        destination_id=dest_match.id
                    ).order_by(PointOfInterest.stars.desc()).limit(15).all()
                    if pois:
                        lines = []
                        for p in pois:
                            line = f"- {p.name} ({p.poi_type})"
                            if p.categories:
                                line += f" — {p.categories}"
                            if p.price_range:
                                line += f" [{p.price_range}]"
                            lines.append(line)
                        poi_hints = "\n".join(lines)

                prompt = build_travel_prompt(
                    destination=destination,
                    duration=duration,
                    budget=budget,
                    travelers=travelers,
                    interests=interests,
                    travel_style=travel_style,
                    start_date=start_date or None,
                    special_requests=special_requests or None,
                    poi_hints=poi_hints,
                )
                itinerary = get_ai_response(client, prompt)

                # Save trip
                trip = Trip(
                    user_id=current_user.id,
                    title=f"{duration}-Day Trip to {destination}",
                    destination_name=destination,
                    itinerary=itinerary,
                    duration_days=duration,
                    budget_level=budget,
                    travelers=travelers,
                    travel_style=travel_style,
                    interests=", ".join(interests),
                )

                if start_date:
                    try:
                        trip.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                    except ValueError:
                        pass

                # Try to link to a destination in our DB
                dest = Destination.query.filter(
                    Destination.name.ilike(f"%{destination}%")
                ).first()
                if dest:
                    trip.destination_id = dest.id

                db.session.add(trip)
                db.session.commit()

                flash("Your travel plan is ready! 🎉", "success")
                return redirect(url_for("trip_detail", trip_id=trip.id))

            except Exception as e:
                flash(f"Error generating plan: {str(e)}", "danger")
                return render_template(
                    "plan_trip.html",
                    top_destinations=top_destinations,
                    suggested_destinations=suggested_destinations,
                )

        return render_template(
            "plan_trip.html",
            top_destinations=top_destinations,
            suggested_destinations=suggested_destinations,
        )

    # ── MY TRIPS ─────────────────────────────────────────────────────────

    @app.route("/my-trips")
    @login_required
    def my_trips():
        """View all saved trips."""
        trips = current_user.trips.order_by(Trip.created_at.desc()).all()
        return render_template("my_trips.html", trips=trips)

    @app.route("/trip/<int:trip_id>")
    @login_required
    def trip_detail(trip_id):
        """View a specific trip."""
        trip = Trip.query.get_or_404(trip_id)
        if trip.user_id != current_user.id:
            abort(403)
        return render_template("trip_detail.html", trip=trip)

    @app.route("/trip/<int:trip_id>/delete", methods=["POST"])
    @login_required
    def delete_trip(trip_id):
        """Delete a saved trip."""
        trip = Trip.query.get_or_404(trip_id)
        if trip.user_id != current_user.id:
            abort(403)
        db.session.delete(trip)
        db.session.commit()
        flash("Trip deleted.", "info")
        return redirect(url_for("my_trips"))

    # ── BUDGET CALCULATOR ────────────────────────────────────────────────

    @app.route("/budget", methods=["GET", "POST"])
    @login_required
    def budget_calculator():
        """AI-powered budget estimation."""
        result = None
        budget_destinations = (
            Destination.query.order_by(
                Destination.is_featured.desc(),
                Destination.rating.desc(),
                Destination.name.asc(),
            )
            .limit(200)
            .all()
        )
        if request.method == "POST":
            destination = request.form.get("destination", "").strip()
            duration = request.form.get("duration", 5, type=int)
            travelers = request.form.get("travelers", 1, type=int)
            budget_level = request.form.get("budget_level", "Mid-Range")

            if not destination:
                flash("Please enter a destination!", "warning")
                return render_template(
                    "budget.html",
                    result=None,
                    budget_destinations=budget_destinations,
                )

            api_key = app.config["NVIDIA_API_KEY"]
            if not api_key:
                flash("NVIDIA API key not configured.", "danger")
                return render_template(
                    "budget.html",
                    result=None,
                    budget_destinations=budget_destinations,
                )

            try:
                client = get_ai_client(api_key)
                prompt = build_budget_prompt(destination, duration, travelers, budget_level)
                result = get_ai_response(client, prompt)
            except Exception as e:
                flash(f"Error: {str(e)}", "danger")

        return render_template(
            "budget.html",
            result=result,
            budget_destinations=budget_destinations,
        )

    # ── CHATBOT ──────────────────────────────────────────────────────────

    @app.route("/chat")
    @login_required
    def chatbot():
        """AI chatbot page."""
        session_id = session.get("chat_session", str(uuid.uuid4()))
        session["chat_session"] = session_id
        messages = ChatMessage.query.filter_by(
            user_id=current_user.id, session_id=session_id
        ).order_by(ChatMessage.created_at.asc()).all()
        return render_template("chatbot.html", messages=messages)

    @app.route("/chat/send", methods=["POST"])
    @login_required
    def chat_send():
        """Send a message to the chatbot (AJAX)."""
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Expected a JSON object"}), 400
        user_message = data.get("message", "")
        if not isinstance(user_message, str):
            return jsonify({"error": "Message must be text"}), 400
        user_message = user_message.strip()
        if len(user_message) > 2000:
            return jsonify({"error": "Message must be 2000 characters or fewer"}), 400

        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        session_id = session.get("chat_session", "default")

        # Save user message
        user_msg = ChatMessage(
            user_id=current_user.id,
            session_id=session_id,
            role="user",
            content=user_message,
        )
        db.session.add(user_msg)
        db.session.commit()

        # Build conversation history
        history = ChatMessage.query.filter_by(
            user_id=current_user.id, session_id=session_id
        ).order_by(ChatMessage.created_at.asc()).all()

        messages = [{"role": m.role, "content": m.content} for m in history[-20:]]  # last 20 messages

        # Get AI response
        api_key = app.config["NVIDIA_API_KEY"]
        if not api_key:
            ai_reply = "Sorry, the AI service is not configured. Please contact the administrator."
        else:
            try:
                client = get_ai_client(api_key)
                ai_reply = chat_response(client, messages)
            except Exception as e:
                ai_reply = f"Sorry, something went wrong: {str(e)}"

        # Save AI response
        ai_msg = ChatMessage(
            user_id=current_user.id,
            session_id=session_id,
            role="assistant",
            content=ai_reply,
        )
        db.session.add(ai_msg)
        db.session.commit()

        return jsonify({"reply": ai_reply})

    @app.route("/chat/clear", methods=["POST"])
    @login_required
    def chat_clear():
        """Clear chat history."""
        session["chat_session"] = str(uuid.uuid4())
        flash("Chat cleared.", "info")
        return redirect(url_for("chatbot"))

    # ── PROFILE ──────────────────────────────────────────────────────────

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        """User profile page."""
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip().lower()
            existing_email = User.query.filter(User.email == email, User.id != current_user.id).first()
            if not email or "@" not in email:
                flash("Enter a valid email address.", "danger")
                return render_template("profile.html")
            if existing_email:
                flash("That email address is already in use.", "danger")
                return render_template("profile.html")

            current_user.full_name = full_name
            current_user.email = email
            current_user.bio = request.form.get("bio", "").strip()
            current_user.favorite_destination = request.form.get("favorite_destination", "").strip()
            current_user.travel_style = request.form.get("travel_style", "Balanced Mix").strip()
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("profile"))

        return render_template("profile.html")

    # ── ERROR HANDLERS ───────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    return app


# ── Entry Point ──────────────────────────────────────────────────────────────
app = create_app()

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_ENV") != "production",
        use_reloader=False,
        port=int(os.getenv("PORT", "5000")),
    )
