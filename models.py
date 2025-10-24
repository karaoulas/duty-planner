"""
SQLAlchemy models for Duty Planner.
Defines Soldier, Assignment, and Unavailability models with relationships.
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()


class Soldier(db.Model):
    """
    Represents a soldier in the unit.
    
    Attributes:
        id: Primary key
        name: Soldier's name (required)
        rank: Military rank (e.g., "Στρατιώτης", "Δεκανέας")
        role: Type of duties they can perform (e.g., "Σκοπιά", "Θαλαμοφύλακας", "Κουζίνα")
        total_services: Total number of times they have been assigned to duty
        is_available: General availability flag
    """
    __tablename__ = 'soldiers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    rank = db.Column(db.String(60))
    role = db.Column(db.String(120), nullable=False)
    total_services = db.Column(db.Integer, default=0)
    is_available = db.Column(db.Boolean, default=True)
    
    # Relationships
    assignments = db.relationship('Assignment', backref='soldier', lazy=True, cascade='all, delete-orphan')
    unavailabilities = db.relationship('Unavailability', backref='soldier', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Soldier {self.id}: {self.name}>'


class Assignment(db.Model):
    """
    Represents an assignment of a soldier to a duty shift on a specific date.
    
    Attributes:
        id: Primary key
        soldier_id: Foreign key to Soldier
        date: Date of the assignment
        shift_type: Type of shift (e.g., "Σκοπιά 00:00-02:00", "Θαλαμοφύλακας Ημέρας")
        confirmed: Whether the assignment has been confirmed
    """
    __tablename__ = 'assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    soldier_id = db.Column(db.Integer, db.ForeignKey('soldiers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.String(120), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Assignment {self.id}: soldier={self.soldier_id}, date={self.date}, shift={self.shift_type}>'


class Unavailability(db.Model):
    """
    Represents a period when a soldier is not available for duty.
    
    Attributes:
        id: Primary key
        soldier_id: Foreign key to Soldier
        date: Date of unavailability
        reason: Reason for unavailability (e.g., "Άδεια", "Υγεία", "Άδεια υπογόμωση")
    """
    __tablename__ = 'unavailabilities'
    
    id = db.Column(db.Integer, primary_key=True)
    soldier_id = db.Column(db.Integer, db.ForeignKey('soldiers.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Unavailability {self.id}: soldier={self.soldier_id}, date={self.date}>'
