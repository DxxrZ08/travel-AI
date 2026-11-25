"""
Database Models — SQLAlchemy ORM
"""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user", server_default="user")
    full_name = db.Column(db.String(150), default="")
    bio = db.Column(db.Text, default="")
    favorite_destination = db.Column(db.String(150), default="")
    travel_style = db.Column(db.String(50), default="Balanced Mix")
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True, index=True)
    avatar_url = db.Column(db.String(500), default="")
    auth_provider = db.Column(db.String(50), default="local")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    trips = db.relationship("Trip", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    reviews = db.relationship("Review", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    chat_messages = db.relationship("ChatMessage", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.username}>"


class Destination(db.Model):
    """Travel destination model."""
    __tablename__ = "destinations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    city = db.Column(db.String(100), default="")
    state = db.Column(db.String(100), default="")
    country = db.Column(db.String(100), default="", index=True)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(50), default="General", index=True)  # Beach, Mountain, Cultural, etc.
    rating = db.Column(db.Float, default=0.0)
    review_count = db.Column(db.Integer, default=0)
    best_time = db.Column(db.String(100), default="Year-round")
    avg_cost_per_day = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(10), default="USD")
    image_url = db.Column(db.String(500), default="")
    latitude = db.Column(db.Float, default=0.0)
    longitude = db.Column(db.Float, default=0.0)
    highlights = db.Column(db.Text, default="")  # Comma-separated highlights
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    trips = db.relationship("Trip", backref="destination", lazy="dynamic")
    reviews = db.relationship("Review", backref="destination", lazy="dynamic", cascade="all, delete-orphan")
    pois = db.relationship("PointOfInterest", backref="destination", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def avg_rating(self):
        """Calculate average rating from reviews."""
        reviews = self.reviews.all()
        if not reviews:
            return self.rating
        return round(sum(r.rating for r in reviews) / len(reviews), 1)

    def __repr__(self):
        return f"<Destination {self.name}>"


class Trip(db.Model):
    """Saved trip / itinerary model."""
    __tablename__ = "trips"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    destination_name = db.Column(db.String(200), default="")
    itinerary = db.Column(db.Text, default="")  # AI-generated markdown
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    duration_days = db.Column(db.Integer, default=1)
    budget_level = db.Column(db.String(50), default="Mid-Range")
    estimated_cost = db.Column(db.Float, default=0.0)
    travelers = db.Column(db.Integer, default=1)
    travel_style = db.Column(db.String(50), default="Balanced Mix")
    interests = db.Column(db.String(500), default="")
    status = db.Column(db.String(20), default="planned")  # planned, ongoing, completed
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Trip {self.title}>"


class Review(db.Model):
    """Destination review model."""
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    title = db.Column(db.String(200), default="")
    comment = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Review {self.rating}★ by User {self.user_id}>"


class ChatMessage(db.Model):
    """Chat history for AI chatbot."""
    __tablename__ = "chat_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(50), default="default")
    role = db.Column(db.String(20), nullable=False)  # user, assistant
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ChatMessage {self.role}: {self.content[:30]}...>"


class PointOfInterest(db.Model):
    """Local Points of Interest (Hotels, Dining, Attractions) from TRACE dataset."""
    __tablename__ = "points_of_interest"

    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey("destinations.id"), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), default="", index=True)
    poi_type = db.Column(db.String(50), default="attraction")  # hotel, restaurant, attraction
    stars = db.Column(db.Float, default=4.0)
    categories = db.Column(db.String(300), default="")
    address = db.Column(db.String(300), default="")
    price_range = db.Column(db.String(20), default="")
    business_id = db.Column(db.String(100), default="", index=True)

    def __repr__(self):
        return f"<POI {self.name} ({self.poi_type}) in {self.city}>"

