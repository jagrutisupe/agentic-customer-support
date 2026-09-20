from datetime import datetime, timedelta

from app.database.connection import SessionLocal
from app.database.models import (
    User,
    Product,
    Order,
    OrderItem,
    Conversation,
    Message,
    SupportTicket,
    AgentLog,
)


def seed_database():
    db = SessionLocal()

    try:
        # Prevent duplicate seed data
        if db.query(User).first():
            print("Database already contains data.")
            return

        # ---------------------------------------------------------
        # USERS
        # ---------------------------------------------------------

        customers = [
            User(
                name="Aarav Sharma",
                email="aarav@example.com",
                password_hash="demo_hash_aarav",
                role="customer",
            ),
            User(
                name="Priya Patil",
                email="priya@example.com",
                password_hash="demo_hash_priya",
                role="customer",
            ),
            User(
                name="Rahul Deshmukh",
                email="rahul@example.com",
                password_hash="demo_hash_rahul",
                role="customer",
            ),
            User(
                name="Sneha Kulkarni",
                email="sneha@example.com",
                password_hash="demo_hash_sneha",
                role="customer",
            ),
            User(
                name="Admin Support",
                email="admin@support.local",
                password_hash="demo_hash_admin",
                role="admin",
            ),
        ]

        db.add_all(customers)
        db.flush()

        # ---------------------------------------------------------
        # PRODUCTS
        # ---------------------------------------------------------

        products = [
            Product(
                name="Wireless Headphones",
                description="Bluetooth over-ear wireless headphones with noise cancellation.",
                category="Audio",
                price=2499.00,
                stock=25,
                warranty_months=12,
            ),
            Product(
                name="Mechanical Keyboard",
                description="RGB mechanical keyboard with blue switches.",
                category="Computer Accessories",
                price=3499.00,
                stock=15,
                warranty_months=12,
            ),
            Product(
                name="Wireless Mouse",
                description="Ergonomic wireless mouse with adjustable DPI.",
                category="Computer Accessories",
                price=1299.00,
                stock=40,
                warranty_months=6,
            ),
            Product(
                name="USB-C Hub",
                description="7-in-1 USB-C hub with HDMI, USB and SD card support.",
                category="Computer Accessories",
                price=1899.00,
                stock=30,
                warranty_months=12,
            ),
            Product(
                name="Smart Watch",
                description="Fitness smartwatch with heart-rate tracking and notifications.",
                category="Wearables",
                price=5999.00,
                stock=10,
                warranty_months=12,
            ),
        ]

        db.add_all(products)
        db.flush()

        # ---------------------------------------------------------
        # ORDERS
        # ---------------------------------------------------------

        now = datetime.utcnow()

        orders = [
            Order(
                order_number="ORD1001",
                customer_id=customers[0].id,
                status="delivered",
                order_date=now - timedelta(days=10),
                expected_delivery=now - timedelta(days=5),
                total_amount=2499.00,
            ),
            Order(
                order_number="ORD1002",
                customer_id=customers[0].id,
                status="shipped",
                order_date=now - timedelta(days=3),
                expected_delivery=now + timedelta(days=2),
                total_amount=3499.00,
            ),
            Order(
                order_number="ORD1003",
                customer_id=customers[1].id,
                status="processing",
                order_date=now - timedelta(days=1),
                expected_delivery=now + timedelta(days=5),
                total_amount=1299.00,
            ),
            Order(
                order_number="ORD1004",
                customer_id=customers[2].id,
                status="cancelled",
                order_date=now - timedelta(days=7),
                expected_delivery=None,
                total_amount=1899.00,
            ),
            Order(
                order_number="ORD1005",
                customer_id=customers[3].id,
                status="shipped",
                order_date=now - timedelta(days=2),
                expected_delivery=now + timedelta(days=3),
                total_amount=5999.00,
            ),
        ]

        db.add_all(orders)
        db.flush()

        # ---------------------------------------------------------
        # ORDER ITEMS
        # ---------------------------------------------------------

        order_items = [
            OrderItem(
                order_id=orders[0].id,
                product_id=products[0].id,
                quantity=1,
                unit_price=2499.00,
            ),
            OrderItem(
                order_id=orders[1].id,
                product_id=products[1].id,
                quantity=1,
                unit_price=3499.00,
            ),
            OrderItem(
                order_id=orders[2].id,
                product_id=products[2].id,
                quantity=1,
                unit_price=1299.00,
            ),
            OrderItem(
                order_id=orders[3].id,
                product_id=products[3].id,
                quantity=1,
                unit_price=1899.00,
            ),
            OrderItem(
                order_id=orders[4].id,
                product_id=products[4].id,
                quantity=1,
                unit_price=5999.00,
            ),
        ]

        db.add_all(order_items)
        db.flush()

        # ---------------------------------------------------------
        # CONVERSATIONS
        # ---------------------------------------------------------

        conversations = [
            Conversation(
                customer_id=customers[0].id,
                session_id="session-aarav-001",
                status="closed",
            ),
            Conversation(
                customer_id=customers[1].id,
                session_id="session-priya-001",
                status="active",
            ),
        ]

        db.add_all(conversations)
        db.flush()

        # ---------------------------------------------------------
        # MESSAGES
        # ---------------------------------------------------------

        messages = [
            Message(
                conversation_id=conversations[0].id,
                sender="customer",
                message="Where is my order ORD1002?",
            ),
            Message(
                conversation_id=conversations[0].id,
                sender="assistant",
                message="Your order ORD1002 has been shipped and is expected to arrive soon.",
            ),
            Message(
                conversation_id=conversations[1].id,
                sender="customer",
                message="Can you tell me about the wireless mouse?",
            ),
        ]

        db.add_all(messages)

        # ---------------------------------------------------------
        # SUPPORT TICKET
        # ---------------------------------------------------------

        ticket = SupportTicket(
            customer_id=customers[2].id,
            subject="Issue with cancelled order",
            description="Customer wants clarification regarding the cancellation of ORD1004.",
            priority="medium",
            status="open",
        )

        db.add(ticket)

        # ---------------------------------------------------------
        # AGENT LOG
        # ---------------------------------------------------------

        agent_log = AgentLog(
            conversation_id=conversations[0].id,
            iteration=1,
            intent="order_status",
            action="lookup_order",
            tool_name="get_order_status",
            tool_input={
                "order_number": "ORD1002"
            },
            tool_output={
                "status": "shipped"
            },
            latency_ms=42.50,
            status="success",
            escalated=False,
        )

        db.add(agent_log)

        # ---------------------------------------------------------
        # COMMIT
        # ---------------------------------------------------------

        db.commit()

        print("========================================")
        print("Database seeded successfully!")
        print("========================================")
        print(f"Users:          {len(customers)}")
        print(f"Products:       {len(products)}")
        print(f"Orders:         {len(orders)}")
        print(f"Order Items:    {len(order_items)}")
        print(f"Conversations:  {len(conversations)}")
        print("Messages:       3")
        print("Tickets:        1")
        print("Agent Logs:     1")
        print("========================================")

    except Exception as error:
        db.rollback()
        print("Error while seeding database:")
        print(error)

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()