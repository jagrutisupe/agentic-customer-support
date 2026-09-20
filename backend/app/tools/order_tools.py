from sqlalchemy.orm import Session

from app.database.models import Order, OrderItem, Product


def get_order_status(
    db: Session,
    order_number: str,
):
    """
    Retrieve order status and basic order information.

    This is a controlled database tool that the future
    AI agent will be allowed to call.
    """

    order = (
        db.query(Order)
        .filter(Order.order_number == order_number)
        .first()
    )

    if not order:
        return {
            "success": False,
            "error": "Order not found",
            "order_number": order_number,
        }

    items = (
        db.query(OrderItem, Product)
        .join(Product, OrderItem.product_id == Product.id)
        .filter(OrderItem.order_id == order.id)
        .all()
    )

    order_items = []

    for item, product in items:
        order_items.append(
            {
                "product_name": product.name,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
            }
        )

    return {
        "success": True,
        "order": {
            "order_number": order.order_number,
            "status": order.status,
            "order_date": order.order_date.isoformat(),
            "expected_delivery": (
                order.expected_delivery.isoformat()
                if order.expected_delivery
                else None
            ),
            "total_amount": float(order.total_amount),
            "items": order_items,
        },
    }