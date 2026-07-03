import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.database import SessionLocal
from app.models import Customer, KnowledgeArticle, PaymentRecord, Subscription

CUSTOMER_1_ID = uuid.UUID("a1000000-0000-0000-0000-000000000001")
CUSTOMER_2_ID = uuid.UUID("a2000000-0000-0000-0000-000000000002")

ARTICLES = [
    {
        "title": "Refund Policy",
        "body": (
            "We offer a full refund within 30 days of purchase for annual plans. "
            "Monthly plans can be cancelled at any time and will not be renewed. "
            "To request a refund, contact support with your account email and order number. "
            "Refunds are processed within 5-7 business days to the original payment method. "
            "Partial refunds are available for unused months on annual plans."
        ),
        "category": "billing",
    },
    {
        "title": "Getting Started",
        "body": (
            "Welcome to the platform. After signing up, you can access your dashboard "
            "to manage projects, invite team members, and configure integrations. "
            "Start by creating your first project and inviting collaborators. "
            "The onboarding wizard will guide you through initial configuration."
        ),
        "category": "onboarding",
    },
    {
        "title": "Account Security and Password Management",
        "body": (
            "Keep your account secure by using a strong, unique password. "
            "You can reset your password from the login page or by contacting support. "
            "We recommend enabling two-factor authentication for additional security. "
            "If you suspect unauthorized access, reset your password immediately and contact support."
        ),
        "category": "security",
    },
    {
        "title": "Subscription Plans",
        "body": (
            "We offer three plans: Starter at $9/month, Professional at $29/month, "
            "and Enterprise with custom pricing. All plans include core features. "
            "Professional adds priority support and advanced analytics. "
            "Enterprise includes dedicated account management and custom integrations. "
            "Annual billing gives a 20% discount on all plans."
        ),
        "category": "billing",
    },
    {
        "title": "Payment Methods and Billing",
        "body": (
            "We accept Visa, Mastercard, American Express, and PayPal. "
            "Invoices are generated at the start of each billing cycle and emailed to "
            "the account owner. If a payment fails, we retry twice over the next 7 days. "
            "You can update your payment method in the billing settings. "
            "Failed payments may result in service interruption after the retry period."
        ),
        "category": "billing",
    },
    {
        "title": "Troubleshooting Login Issues",
        "body": (
            "If you cannot log in, first check that you are using the correct email address. "
            "Try resetting your password using the 'Forgot Password' link. "
            "Clear your browser cache and cookies if the login page does not load. "
            "Ensure your browser is up to date. Contact support if the issue persists."
        ),
        "category": "support",
    },
    {
        "title": "Data Export and Portability",
        "body": (
            "You can export your data at any time from the account settings page. "
            "Exports are available in CSV and JSON formats. Large exports are processed "
            "in the background and you will receive an email when the file is ready. "
            "Exported data includes projects, tasks, and associated metadata."
        ),
        "category": "features",
    },
    {
        "title": "Contacting Support",
        "body": (
            "Reach our support team via email at support@example.com or through the "
            "in-app chat widget. Support hours are Monday through Friday, 9am to 6pm EST. "
            "Professional and Enterprise plan customers receive priority response times. "
            "For urgent issues outside business hours, use the emergency contact form."
        ),
        "category": "support",
    },
]


def seed():
    db = SessionLocal()
    try:
        if db.query(Customer).first():
            return

        db.add_all([
            Customer(id=CUSTOMER_1_ID, email="alice@example.com", name="Alice Johnson"),
            Customer(id=CUSTOMER_2_ID, email="bob@example.com", name="Bob Smith"),
        ])

        db.add_all([KnowledgeArticle(**a) for a in ARTICLES])

        now = datetime.now(UTC)
        db.add_all([
            Subscription(
                customer_id=CUSTOMER_1_ID,
                plan="professional",
                status="active",
                current_period_end=now + timedelta(days=25),
            ),
            Subscription(
                customer_id=CUSTOMER_2_ID,
                plan="starter",
                status="past_due",
                current_period_end=now - timedelta(days=3),
            ),
        ])

        db.add_all([
            PaymentRecord(
                customer_id=CUSTOMER_1_ID,
                amount=Decimal("29.00"),
                status="succeeded",
            ),
            PaymentRecord(
                customer_id=CUSTOMER_2_ID,
                amount=Decimal("9.00"),
                status="succeeded",
            ),
            PaymentRecord(
                customer_id=CUSTOMER_2_ID,
                amount=Decimal("9.00"),
                status="failed",
                failure_reason="card_expired",
            ),
        ])

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print("Seed complete.")
