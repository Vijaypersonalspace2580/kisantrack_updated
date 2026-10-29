"""KisanTrak API starter. Configure DATABASE_URL and SECRET_KEY before deployment."""
import os, secrets, json
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from passlib.context import CryptContext
from jose import jwt, JWTError

DATABASE_URL=os.getenv('DATABASE_URL','sqlite:///./kisantrak.db')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://", "postgresql+psycopg://", 1
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
engine=create_engine(DATABASE_URL,connect_args={'check_same_thread':False} if DATABASE_URL.startswith('sqlite') else {},pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
SECRET_KEY=os.getenv('SECRET_KEY')
if not SECRET_KEY: SECRET_KEY=secrets.token_urlsafe(48); print('WARNING: SECRET_KEY not set. Sessions will not survive a restart. Set a persistent SECRET_KEY in production.')
ALGORITHM='HS256'; pwd=CryptContext(schemes=['bcrypt'],deprecated='auto')
class Base(DeclarativeBase): pass
class Admin(Base):
    __tablename__='admins'; id:Mapped[int]=mapped_column(primary_key=True); name:Mapped[str]=mapped_column(String(120)); phone:Mapped[str]=mapped_column(String(20),unique=True,index=True); password_hash:Mapped[str]=mapped_column(String(255)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Customer(Base):
    __tablename__='customers'; id:Mapped[int]=mapped_column(primary_key=True); phone:Mapped[str]=mapped_column(String(20),unique=True,index=True); name:Mapped[str]=mapped_column(String(120)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Work(Base):
    __tablename__='work_records'; id:Mapped[str]=mapped_column(String(64),primary_key=True); phone:Mapped[str]=mapped_column(String(20),index=True); name:Mapped[str]=mapped_column(String(120)); instrument:Mapped[str]=mapped_column(String(80)); start:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); end:Mapped[Optional[str]]=mapped_column(String(40),nullable=True); duration_hours:Mapped[float]=mapped_column(Float,default=0); rate:Mapped[float]=mapped_column(Float,default=0); total:Mapped[float]=mapped_column(Float,default=0); status:Mapped[str]=mapped_column(String(20),default='complete'); notes:Mapped[str]=mapped_column(Text,default=''); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class SyncState(Base):
    __tablename__='sync_states'; admin_id:Mapped[int]=mapped_column(ForeignKey('admins.id'),primary_key=True); state_json:Mapped[str]=mapped_column(Text,default='{}'); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class Payment(Base):
    __tablename__='payments'; id:Mapped[str]=mapped_column(String(64),primary_key=True); job_id:Mapped[Optional[str]]=mapped_column(String(64),nullable=True); phone:Mapped[str]=mapped_column(String(20),index=True); name:Mapped[str]=mapped_column(String(120)); amount:Mapped[float]=mapped_column(Float); mode:Mapped[str]=mapped_column(String(40)); reference:Mapped[str]=mapped_column(String(160),default=''); verified:Mapped[bool]=mapped_column(Boolean,default=False); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
Base.metadata.create_all(engine)
app=FastAPI(title='KisanTrak API',version='1.0.0',description='Secure API starter for tractor work, customer and payment records')
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://kisantrack-app.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5500,http://127.0.0.1:5500').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['GET','POST','PUT','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'])
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
class RegisterIn(BaseModel): name:str=Field(min_length=1,max_length=120); phone:str=Field(min_length=10,max_length=16); password:str=Field(min_length=8,max_length=128)
class LoginIn(BaseModel): phone:str; password:str
class WorkIn(BaseModel): id:str=Field(min_length=1,max_length=64); phone:str; name:str; instrument:str; start:Optional[str]=None; end:Optional[str]=None; duration_hours:float=Field(default=0,ge=0); rate:float=Field(ge=0); total:float=Field(ge=0); status:str='complete'; notes:str=''
class PaymentIn(BaseModel): id:str; job_id:Optional[str]=None; phone:str; name:str; amount:float=Field(gt=0); mode:str; reference:str=''
def token_for(admin): return jwt.encode({'sub':str(admin.id),'exp':datetime.now(timezone.utc)+timedelta(hours=12)},SECRET_KEY,algorithm=ALGORITHM)
def current_admin(authorization:str=Header(default=''),db:Session=Depends(get_db)):
    if not authorization.startswith('Bearer '): raise HTTPException(401,'Bearer token required')
    try: payload=jwt.decode(authorization[7:],SECRET_KEY,algorithms=[ALGORITHM]); admin_id=int(payload['sub'])
    except (JWTError,ValueError,KeyError): raise HTTPException(401,'Invalid or expired session')
    admin=db.get(Admin,admin_id)
    if not admin: raise HTTPException(401,'Admin account not found')
    return admin
@app.get('/')
def root(): return {'service':'KisanTrak API','status':'running','docs':'/docs'}
@app.get('/api/health')
def health(): return {'status':'ok'}
@app.post('/api/auth/register')
def register(body:RegisterIn,db:Session=Depends(get_db)):
    if db.query(Admin).first(): raise HTTPException(403,'Admin already registered. Ask your existing admin.')
    phone=body.phone.strip()
    if db.query(Admin).filter_by(phone=phone).first(): raise HTTPException(409,'Phone number already registered')
    a=Admin(name=body.name.strip(),phone=phone,password_hash=pwd.hash(body.password));db.add(a);db.commit();db.refresh(a)
    return {'access_token':token_for(a),'token_type':'bearer','admin':{'name':a.name,'phone':a.phone}}
@app.post('/api/auth/login')
def login(body:LoginIn,db:Session=Depends(get_db)):
    a=db.query(Admin).filter_by(phone=body.phone.strip()).first()
    if not a or not pwd.verify(body.password,a.password_hash): raise HTTPException(401,'Incorrect phone number or password')
    return {'access_token':token_for(a),'token_type':'bearer','admin':{'name':a.name,'phone':a.phone}}
class SyncIn(BaseModel): state:dict
@app.get('/api/sync')
def get_sync_state(db:Session=Depends(get_db),admin=Depends(current_admin)):
    row=db.get(SyncState,admin.id)
    if not row:return {'state':None,'updated_at':None}
    try: state=json.loads(row.state_json)
    except Exception: state=None
    return {'state':state,'updated_at':row.updated_at.isoformat() if row.updated_at else None}
@app.put('/api/sync')
def put_sync_state(body:SyncIn,db:Session=Depends(get_db),admin=Depends(current_admin)):
    # Full local app snapshot stored per authenticated admin; payload capped to protect service resources.
    encoded=json.dumps(body.state,separators=(',',':'))
    if len(encoded)>5_000_000: raise HTTPException(413,'Backup is too large (maximum 5 MB)')
    row=db.get(SyncState,admin.id)
    if row: row.state_json=encoded; row.updated_at=datetime.utcnow()
    else: db.add(SyncState(admin_id=admin.id,state_json=encoded))
    db.commit()
    return {'ok':True,'updated_at':datetime.utcnow().isoformat()}
@app.get('/api/customers')
def customers(db:Session=Depends(get_db),admin=Depends(current_admin)):
    return [{'id':c.id,'phone':c.phone,'name':c.name,'created_at':c.created_at.isoformat()} for c in db.query(Customer).order_by(Customer.name).all()]
@app.post('/api/customers')
def add_customer(body:RegisterIn,db:Session=Depends(get_db),admin=Depends(current_admin)):
    c=db.query(Customer).filter_by(phone=body.phone.strip()).first()
    if c: c.name=body.name.strip()
    else: c=Customer(phone=body.phone.strip(),name=body.name.strip());db.add(c)
    db.commit();db.refresh(c);return {'id':c.id,'phone':c.phone,'name':c.name}
@app.get('/api/work')
def list_work(db:Session=Depends(get_db),admin=Depends(current_admin)):
    return [{'id':w.id,'phone':w.phone,'name':w.name,'instrument':w.instrument,'start':w.start,'end':w.end,'duration_hours':w.duration_hours,'rate':w.rate,'total':w.total,'status':w.status,'notes':w.notes,'created_at':w.created_at.isoformat()} for w in db.query(Work).order_by(Work.created_at.desc()).all()]
@app.post('/api/work')
def upsert_work(body:WorkIn,db:Session=Depends(get_db),admin=Depends(current_admin)):
    phone=body.phone.strip(); c=db.query(Customer).filter_by(phone=phone).first()
    if c:c.name=body.name.strip()
    else:db.add(Customer(phone=phone,name=body.name.strip()))
    w=db.get(Work,body.id)
    if not w:w=Work(id=body.id,phone=phone,name=body.name.strip(),instrument=body.instrument,rate=body.rate,total=body.total);db.add(w)
    for key,val in body.model_dump().items(): setattr(w,key,val)
    db.commit();return {'ok':True,'id':w.id}
@app.delete('/api/work/{work_id}')
def delete_work(work_id:str,db:Session=Depends(get_db),admin=Depends(current_admin)):
    w=db.get(Work,work_id)
    if not w:raise HTTPException(404,'Work record not found')
    db.delete(w);db.commit();return {'ok':True}
@app.get('/api/payments')
def list_payments(db:Session=Depends(get_db),admin=Depends(current_admin)):
    return [{'id':p.id,'job_id':p.job_id,'phone':p.phone,'name':p.name,'amount':p.amount,'mode':p.mode,'reference':p.reference,'verified':p.verified,'created_at':p.created_at.isoformat()} for p in db.query(Payment).order_by(Payment.created_at.desc()).all()]
@app.post('/api/payments')
def add_payment(body:PaymentIn,db:Session=Depends(get_db),admin=Depends(current_admin)):
    if db.get(Payment,body.id): return {'ok':True,'id':body.id,'duplicate':True}
    p=Payment(**body.model_dump());db.add(p);db.commit();return {'ok':True,'id':p.id,'verified':False,'message':'Payment recorded; verify receipt manually in admin workflow.'}
@app.post('/api/payments/{payment_id}/verify')
def verify_payment(payment_id:str,db:Session=Depends(get_db),admin=Depends(current_admin)):
    p=db.get(Payment,payment_id)
    if not p:raise HTTPException(404,'Payment not found')
    p.verified=True;db.commit();return {'ok':True,'verified':True}
