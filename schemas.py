"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class SizeStock(BaseModel):
    size: str = Field(..., description="Size label, e.g., S, M, L, XL")
    stock: int = Field(..., ge=0, description="Units in stock for this size")


class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    slug: str = Field(..., description="URL-friendly unique identifier")
    name: str = Field(..., description="Product display name")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Category like hoodies, sneakers")
    accent: str = Field("#7CFF2E", description="Neon accent color for the product card")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    sizes: List[SizeStock] = Field(default_factory=list, description="Size and stock info")
    is_limited: bool = Field(True, description="If this is a limited drop")


class OTPRequest(BaseModel):
    phone: str = Field(..., description="E.164 formatted phone number")


class OTPVerify(BaseModel):
    phone: str
    code: str


# Example additional models could go here if needed
