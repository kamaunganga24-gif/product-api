# main.py
import time
import os
import psutil
import platform
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import Session, select
from passlib.context import CryptContext
from jose import JWTError, jwt

from database.session import get_session, init_db
from models.product import Product, ProductCreate, ProductUpdate, Category, CategoryCreate
from models.user import User, UserCreate, UserResponse, Token

# Setup Logging
LOG_FILE = os.getenv("LOG_FILE", "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(LOG_FILE, maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("product-api")

# Auth Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Lifespan Context Manager (replaces @app.on_event("startup"))
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Product Catalog API", version="1.0.0", lifespan=lifespan)
start_time = time.time()

# Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    req_start = time.time()
    response = await call_next(request)
    process_time = time.time() - req_start
    logger.info(f"{request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    return response

# Auth Helper Functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = session.exec(select(User).where(User.username == username)).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return current_user

# ==================== AUTH ENDPOINTS ====================
@app.post("/register", response_model=UserResponse, status_code=201)
def register(user_in: UserCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where((User.username == user_in.username) | (User.email == user_in.email))).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username or email already exists")
    
    hashed_pw = get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hashed_pw
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users", response_model=List[UserResponse])
def get_users(admin: User = Depends(get_current_admin), session: Session = Depends(get_session)):
    return session.exec(select(User)).all()

# ==================== CATEGORY ENDPOINTS ====================
@app.post("/categories", response_model=Category, status_code=201)
def create_category(category: CategoryCreate, session: Session = Depends(get_session)):
    existing = session.exec(select(Category).where(Category.name == category.name)).first()
    if existing:
        raise HTTPException(400, "Category already exists")
    db_category = Category(**category.model_dump())
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category

@app.get("/categories", response_model=List[Category])
def list_categories(session: Session = Depends(get_session)):
    return session.exec(select(Category)).all()

# ==================== PRODUCT ENDPOINTS ====================
@app.post("/products", response_model=Product, status_code=201)
def create_product(product: ProductCreate, session: Session = Depends(get_session)):
    if product.category_id:
        if not session.get(Category, product.category_id):
            raise HTTPException(404, "Category not found")
    db_product = Product(**product.model_dump())
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    return db_product

@app.get("/products", response_model=List[Product])
def list_products(
    skip: int = 0, limit: int = 10,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    query = select(Product)
    if category_id: query = query.where(Product.category_id == category_id)
    if min_price is not None: query = query.where(Product.price >= min_price)
    if max_price is not None: query = query.where(Product.price <= max_price)
    if in_stock is not None:
        query = query.where(Product.stock > 0) if in_stock else query.where(Product.stock == 0)
    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/products/search", response_model=List[Product])
def search_products(q: str, session: Session = Depends(get_session)):
    query = select(Product).where((Product.name.contains(q)) | (Product.description.contains(q)))
    return session.exec(query).all()

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product: raise HTTPException(404, "Product not found")
    return product

@app.patch("/products/{product_id}", response_model=Product)
def update_product(product_id: int, product_update: ProductUpdate, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product: raise HTTPException(404, "Product not found")
    for key, value in product_update.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    product.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(product)
    return product

@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product: raise HTTPException(404, "Product not found")
    session.delete(product)
    session.commit()
    return None

# ==================== MONITORING ENDPOINTS ====================
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "uptime": time.time() - start_time,
        "system": {"platform": platform.platform(), "python": platform.python_version()}
    }

@app.get("/metrics")
def get_metrics(current_user: User = Depends(get_current_admin)):
    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent
    }