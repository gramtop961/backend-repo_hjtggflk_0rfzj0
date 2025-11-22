import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from database import db, create_document
from schemas import Product as ProductSchema, SizeStock, OTPRequest, OTPVerify
from bson import ObjectId

app = FastAPI(title="The Drop Zone API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"brand": "The Drop Zone", "message": "Backend running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "❌ Unknown"
            _ = db.list_collection_names()
            response["collections"] = _
            response["database"] = "✅ Connected & Working"
            response["connection_status"] = "Connected"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:120]}"
    return response


# ----------------------------- Auth (Phone + OTP - demo) -----------------------------
# NOTE: This demo does not send real SMS. It stores a one-time code '123456' for the phone.
# Do NOT use in production.

@app.post("/api/auth/otp/request")
def request_otp(payload: OTPRequest):
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone required")
    # Upsert pending OTP document
    db["otp"].update_one({"phone": phone}, {"$set": {"phone": phone, "code": "123456"}}, upsert=True)
    return {"ok": True, "message": "OTP sent (demo)", "code_demo": "123456"}


@app.post("/api/auth/otp/verify")
def verify_otp(payload: OTPVerify):
    doc = db["otp"].find_one({"phone": payload.phone})
    if not doc or payload.code != doc.get("code"):
        raise HTTPException(status_code=401, detail="Invalid code")
    # Create a very basic session id
    session_id = str(ObjectId())
    db["session"].insert_one({"_id": ObjectId(session_id), "phone": payload.phone})
    return {"ok": True, "session_id": session_id}


# ----------------------------- Products -----------------------------

class QuickAdd(BaseModel):
    slug: str
    size: Optional[str] = None
    qty: int = 1


@app.get("/api/products")
def list_products(category: Optional[str] = None):
    q = {}
    if category:
        q["category"] = category
    products = list(db["product"].find(q).limit(60))
    for p in products:
        p["_id"] = str(p["_id"])  # serialize
    return {"items": products}


@app.get("/api/products/{slug}")
def get_product(slug: str):
    p = db["product"].find_one({"slug": slug})
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    p["_id"] = str(p["_id"])
    return p


@app.post("/api/seed-products")
def seed_products():
    count = db["product"].count_documents({})
    if count > 0:
        return {"ok": True, "message": "Products already seeded", "count": count}

    sample: List[ProductSchema] = [
        ProductSchema(
            slug="stealth-hoodie",
            name="Stealth Hoodie",
            description="Matte black heavyweight hoodie with reflective piping.",
            price=120.0,
            category="hoodies",
            accent="#7CFF2E",
            images=[
                "https://images.unsplash.com/photo-1516826957135-700dedea698c?q=80&w=1600&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2?q=80&w=1600&auto=format&fit=crop"
            ],
            sizes=[
                SizeStock(size="S", stock=8),
                SizeStock(size="M", stock=2),
                SizeStock(size="L", stock=0),
                SizeStock(size="XL", stock=5),
            ],
            is_limited=True,
        ),
        ProductSchema(
            slug="crest-tee",
            name="Crest Tee",
            description="Concrete grey oversized tee with neon crest.",
            price=55.0,
            category="tees",
            accent="#00E5FF",
            images=[
                "https://images.unsplash.com/photo-1519741497674-611481863552?q=80&w=1600&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?q=80&w=1600&auto=format&fit=crop"
            ],
            sizes=[
                SizeStock(size="S", stock=15),
                SizeStock(size="M", stock=12),
                SizeStock(size="L", stock=6),
                SizeStock(size="XL", stock=1),
            ],
            is_limited=False,
        ),
        ProductSchema(
            slug="volt-sneaker",
            name="Volt Sneaker",
            description="Electric green accent sneaker with urban tread.",
            price=220.0,
            category="sneakers",
            accent="#7CFF2E",
            images=[
                "https://images.unsplash.com/photo-1542291026-7eec264c27ff?q=80&w=1600&auto=format&fit=crop",
                "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?q=80&w=1600&auto=format&fit=crop"
            ],
            sizes=[
                SizeStock(size="7", stock=3),
                SizeStock(size="8", stock=0),
                SizeStock(size="9", stock=4),
                SizeStock(size="10", stock=2),
            ],
            is_limited=True,
        ),
    ]

    for prod in sample:
        create_document("product", prod)

    seeded = db["product"].count_documents({})
    return {"ok": True, "message": "Seeded", "count": seeded}


# ----------------------------- Cart -----------------------------

@app.get("/api/cart/{cart_id}")
def get_cart(cart_id: str):
    cart = db["cart"].find_one({"_id": cart_id})
    if not cart:
        cart = {"_id": cart_id, "items": [], "subtotal": 0}
        db["cart"].insert_one(cart)
    # enrich with product info
    subtotal = 0
    for item in cart["items"]:
        p = db["product"].find_one({"slug": item["slug"]})
        if p:
            item["name"] = p.get("name")
            item["price"] = p.get("price")
            item["accent"] = p.get("accent")
            item["image"] = (p.get("images") or [None])[0]
            subtotal += item.get("qty", 1) * float(p.get("price", 0))
    cart["subtotal"] = round(subtotal, 2)
    return cart


@app.post("/api/cart/{cart_id}/add")
def add_to_cart(cart_id: str, payload: QuickAdd):
    p = db["product"].find_one({"slug": payload.slug})
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")
    # default size: choose first available if not provided
    size = payload.size
    if not size:
        sizes = p.get("sizes") or []
        size = next((s.get("size") for s in sizes if s.get("stock", 0) > 0), None)
    if not size:
        raise HTTPException(status_code=400, detail="No available size")

    cart = db["cart"].find_one({"_id": cart_id})
    if not cart:
        cart = {"_id": cart_id, "items": []}
        db["cart"].insert_one(cart)

    # check if item exists
    exists = next((i for i in cart["items"] if i["slug"] == payload.slug and i.get("size") == size), None)
    if exists:
        exists["qty"] = exists.get("qty", 1) + max(1, payload.qty)
    else:
        cart["items"].append({"slug": payload.slug, "size": size, "qty": max(1, payload.qty)})
    db["cart"].update_one({"_id": cart_id}, {"$set": {"items": cart["items"]}})
    return {"ok": True}


class UpdateItem(BaseModel):
    slug: str
    size: str
    qty: Optional[int] = None
    remove: Optional[bool] = False


@app.post("/api/cart/{cart_id}/update")
def update_cart(cart_id: str, payload: UpdateItem):
    cart = db["cart"].find_one({"_id": cart_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    items = cart.get("items", [])
    new_items = []
    for it in items:
        if it["slug"] == payload.slug and it.get("size") == payload.size:
            if payload.remove or (payload.qty is not None and payload.qty <= 0):
                continue
            if payload.qty is not None:
                it["qty"] = payload.qty
        new_items.append(it)
    db["cart"].update_one({"_id": cart_id}, {"$set": {"items": new_items}})
    return {"ok": True}
