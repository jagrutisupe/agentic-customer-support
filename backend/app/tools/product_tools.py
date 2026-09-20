from sqlalchemy.orm import Session

from app.database.models import Product


def search_products(
    db: Session,
    query: str,
):
    """
    Search products by name, description, or category.

    This is a controlled database tool that the AI agent
    will be allowed to call.
    """

    search_term = query.strip().lower()

    if not search_term:
        return {
            "success": False,
            "error": "Search query cannot be empty",
            "products": [],
        }

    products = (
        db.query(Product)
        .filter(
            (Product.name.ilike(f"%{search_term}%"))
            | (Product.description.ilike(f"%{search_term}%"))
            | (Product.category.ilike(f"%{search_term}%"))
        )
        .all()
    )

    results = []

    for product in products:
        results.append(
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": float(product.price),
                "stock": product.stock,
                "warranty_months": product.warranty_months,
            }
        )

    return {
        "success": True,
        "query": query,
        "count": len(results),
        "products": results,
    }

def get_product_details(
    db: Session,
    product_id: int,
):
    """
    Retrieve complete details for a specific product.
    """

    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        return {
            "success": False,
            "message": f"Product {product_id} was not found.",
        }

    return {
        "success": True,
        "product": {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "price": product.price,
            "stock": product.stock,
            "warranty_months": product.warranty_months,
        },
    }