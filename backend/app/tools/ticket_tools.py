from datetime import datetime

from sqlalchemy.orm import Session

from app.database.models import SupportTicket


def create_support_ticket(
    db: Session,
    customer_id: int,
    subject: str,
    description: str,
    priority: str = "medium",
):
    """
    Create a new support ticket for a customer.
    """

    ticket = SupportTicket(
        customer_id=customer_id,
        subject=subject,
        description=description,
        priority=priority,
        status="open",
        assigned_to=None,
        created_at=datetime.utcnow(),
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return {
        "success": True,
        "message": "Support ticket created successfully",
        "ticket": {
            "id": ticket.id,
            "customer_id": ticket.customer_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_to": ticket.assigned_to,
            "created_at": ticket.created_at,
        },
    }


def get_ticket_status(
    db: Session,
    ticket_id: int,
):
    """
    Retrieve the current status and details of a support ticket.
    """

    ticket = (
        db.query(SupportTicket)
        .filter(SupportTicket.id == ticket_id)
        .first()
    )

    if not ticket:
        return {
            "success": False,
            "message": f"Support ticket {ticket_id} was not found.",
        }

    return {
        "success": True,
        "ticket": {
            "id": ticket.id,
            "customer_id": ticket.customer_id,
            "subject": ticket.subject,
            "description": ticket.description,
            "priority": ticket.priority,
            "status": ticket.status,
            "assigned_to": ticket.assigned_to,
            "created_at": ticket.created_at,
            "resolved_at": ticket.resolved_at,
        },
    }