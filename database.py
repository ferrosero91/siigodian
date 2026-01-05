"""Modelos de base de datos con SQLAlchemy"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ============== TABLAS DE CATÁLOGOS ==============

class TypeDocumentIdentification(Base):
    """Tipos de documento de identificación"""
    __tablename__ = "type_document_identifications"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    code = Column(String(10))


class TypeOrganization(Base):
    """Tipos de organización"""
    __tablename__ = "type_organizations"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    code = Column(String(10))


class TypeRegime(Base):
    """Tipos de régimen tributario"""
    __tablename__ = "type_regimes"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    code = Column(String(10))


class TypeLiability(Base):
    """Tipos de responsabilidad tributaria"""
    __tablename__ = "type_liabilities"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    code = Column(String(20))


class Department(Base):
    """Departamentos de Colombia"""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, default=46)
    name = Column(String(100))
    code = Column(String(10))
    
    municipalities = relationship("Municipality", back_populates="department")


class Municipality(Base):
    """Municipios de Colombia"""
    __tablename__ = "municipalities"
    
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    name = Column(String(100))
    code = Column(String(10))
    codefacturador = Column(String(10))
    
    department = relationship("Department", back_populates="municipalities")


class Settings(Base):
    """Configuración de la empresa y API"""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, default=1)
    # Empresa
    company_name = Column(String(200))
    company_nit = Column(String(20))
    company_dv = Column(String(1))
    company_address = Column(String(200))
    company_phone = Column(String(20))
    company_email = Column(String(100))
    merchant_registration = Column(String(50), default="0000000-00")
    department_id = Column(Integer, default=22)  # Nariño
    municipality_id = Column(Integer, default=520)  # Pasto
    type_document_identification_id = Column(Integer, default=3)  # Cédula
    type_organization_id = Column(Integer, default=2)  # Persona Natural
    type_regime_id = Column(Integer, default=2)  # No Responsable IVA
    type_liability_id = Column(Integer, default=117)  # No responsable
    # API - Facturación
    api_url = Column(String(200), default="https://apidian.clipers.pro/api/ubl2.1")
    api_token = Column(String(100))
    software_id = Column(String(100))
    software_pin = Column(String(10))
    test_set_id = Column(String(100))
    type_environment_id = Column(Integer, default=2)  # 1=Producción, 2=Habilitación
    # API - Documento Soporte
    ds_software_id = Column(String(100))
    ds_software_pin = Column(String(10))
    ds_test_set_id = Column(String(100))
    # Certificado
    certificate_path = Column(String(500))
    certificate_password = Column(String(100))
    # Correo SMTP
    mail_host = Column(String(100), default="smtp.gmail.com")
    mail_port = Column(Integer, default=587)
    mail_username = Column(String(100))
    mail_password = Column(String(100))
    mail_encryption = Column(String(10), default="tls")
    # Carpetas
    watch_folder = Column(String(500))
    processed_folder = Column(String(500))
    
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Resolution(Base):
    """Resoluciones de facturación"""
    __tablename__ = "resolutions"
    
    id = Column(Integer, primary_key=True)
    type_document_id = Column(Integer)  # 1=Factura, 4=NC, 5=ND
    type_document_name = Column(String(50))
    prefix = Column(String(10))
    resolution = Column(String(50))
    resolution_date = Column(DateTime)
    technical_key = Column(String(100))
    from_number = Column(Integer, name="from")
    to_number = Column(Integer, name="to")
    current_number = Column(Integer, default=0)
    date_from = Column(DateTime)
    date_to = Column(DateTime)
    is_active = Column(Boolean, default=True)
    synced_with_api = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Document(Base):
    """Documentos electrónicos"""
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    type = Column(String(20))  # invoice, credit_note, debit_note, support_document
    type_document_id = Column(Integer)
    prefix = Column(String(10))
    number = Column(String(20))
    full_number = Column(String(30))
    issue_date = Column(DateTime)
    
    # Cliente/Proveedor
    customer_nit = Column(String(20))
    customer_name = Column(String(200))
    customer_email = Column(String(100))
    
    # Montos
    subtotal = Column(Float, default=0)
    total_tax = Column(Float, default=0)
    total_discount = Column(Float, default=0)
    total = Column(Float, default=0)
    
    # Estado
    status = Column(String(20), default="pending")  # pending, processing, sent, error, rejected
    cufe = Column(String(200))
    error_message = Column(Text)
    is_nullified = Column(Boolean, default=False)  # Marcado como anulado por NC
    
    # XML
    xml_content = Column(Text)
    xml_filename = Column(String(100))
    
    # Datos parseados y respuesta API
    parsed_data = Column(JSON)
    api_request = Column(JSON)
    api_response = Column(JSON)
    
    # Referencia (para NC/ND)
    reference_document_id = Column(Integer, ForeignKey("documents.id"))
    reference_cufe = Column(String(200))
    
    # Tracking de acciones
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime)
    pdf_downloaded = Column(Boolean, default=False)
    pdf_downloaded_at = Column(DateTime)
    
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relación
    reference_document = relationship("Document", remote_side=[id])

    @property
    def status_label(self):
        labels = {
            "pending": "Pendiente",
            "processing": "Procesando",
            "sent": "Procesado Correctamente",
            "error": "Error",
            "rejected": "Rechazado"
        }
        return labels.get(self.status, self.status)
    
    @property
    def type_label(self):
        labels = {
            "invoice": "Factura",
            "credit_note": "Nota Crédito",
            "debit_note": "Nota Débito",
            "support_document": "Doc. Soporte",
            "sd_adjustment_note": "Nota Ajuste DS"
        }
        return labels.get(self.type, self.type)


class Customer(Base):
    """Clientes/Proveedores"""
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True)
    type = Column(String(20), default="customer")  # customer, supplier
    identification_number = Column(String(20), unique=True)
    dv = Column(String(1))
    name = Column(String(200))
    trade_name = Column(String(200))  # Nombre comercial
    phone = Column(String(50))
    email = Column(String(100))
    address = Column(String(200))
    
    # Clasificación tributaria
    type_document_identification_id = Column(Integer, default=3)  # Cédula
    type_organization_id = Column(Integer, default=2)  # Persona Natural
    type_regime_id = Column(Integer, default=2)  # No Responsable IVA
    type_liability_id = Column(Integer, default=117)  # No responsable
    
    # Ubicación
    department_id = Column(Integer)
    municipality_id = Column(Integer)
    
    # Estado
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Product(Base):
    """Productos/Servicios"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True)
    name = Column(String(200))
    description = Column(Text)
    
    # Precios
    unit_price = Column(Float, default=0)
    tax_percent = Column(Float, default=0)  # 0, 5, 19
    
    # Clasificación
    type_item_identification_id = Column(Integer, default=4)  # Estándar de adopción del contribuyente
    unit_measure_id = Column(Integer, default=70)  # Unidad
    
    # Stock (opcional)
    stock = Column(Float, default=0)
    min_stock = Column(Float, default=0)
    
    # Estado
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_db():
    """Inicializar base de datos y poblar catálogos"""
    Base.metadata.create_all(engine)
    
    # Ejecutar migraciones para columnas nuevas
    _run_migrations()
    
    session = SessionLocal()
    
    # Crear settings por defecto si no existe
    if not session.query(Settings).first():
        session.add(Settings())
        session.commit()
    
    # Poblar catálogos si están vacíos
    _populate_catalogs(session)
    
    session.close()


def _run_migrations():
    """Ejecutar migraciones para agregar columnas nuevas"""
    from sqlalchemy import text
    
    with engine.connect() as conn:
        # Verificar y agregar columnas de tracking en documents
        try:
            conn.execute(text("SELECT email_sent FROM documents LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE documents ADD COLUMN email_sent TINYINT(1) DEFAULT 0"))
                conn.commit()
            except:
                pass
        
        try:
            conn.execute(text("SELECT email_sent_at FROM documents LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE documents ADD COLUMN email_sent_at DATETIME NULL"))
                conn.commit()
            except:
                pass
        
        try:
            conn.execute(text("SELECT pdf_downloaded FROM documents LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE documents ADD COLUMN pdf_downloaded TINYINT(1) DEFAULT 0"))
                conn.commit()
            except:
                pass
        
        try:
            conn.execute(text("SELECT pdf_downloaded_at FROM documents LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE documents ADD COLUMN pdf_downloaded_at DATETIME NULL"))
                conn.commit()
            except:
                pass
        
        # Columnas para Documento Soporte en settings
        try:
            conn.execute(text("SELECT ds_software_id FROM settings LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE settings ADD COLUMN ds_software_id VARCHAR(100) NULL"))
                conn.commit()
            except:
                pass
        
        try:
            conn.execute(text("SELECT ds_software_pin FROM settings LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE settings ADD COLUMN ds_software_pin VARCHAR(10) NULL"))
                conn.commit()
            except:
                pass
        
        try:
            conn.execute(text("SELECT ds_test_set_id FROM settings LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE settings ADD COLUMN ds_test_set_id VARCHAR(100) NULL"))
                conn.commit()
            except:
                pass
        
        # Columna para marcar facturas anuladas por NC
        try:
            conn.execute(text("SELECT is_nullified FROM documents LIMIT 1"))
        except:
            try:
                conn.execute(text("ALTER TABLE documents ADD COLUMN is_nullified TINYINT(1) DEFAULT 0"))
                conn.commit()
            except:
                pass


def _populate_catalogs(session):
    """Poblar tablas de catálogos"""
    
    # Tipos de documento de identificación
    if session.query(TypeDocumentIdentification).count() == 0:
        data = [
            (1, "Registro civil", "11"),
            (2, "Tarjeta de identidad", "12"),
            (3, "Cédula de ciudadanía", "13"),
            (4, "Tarjeta de extranjería", "21"),
            (5, "Cédula de extranjería", "22"),
            (6, "NIT", "31"),
            (7, "Pasaporte", "41"),
            (8, "Documento de identificación extranjero", "42"),
            (9, "NIT de otro país", "50"),
            (10, "NUIP", "91"),
        ]
        for id, name, code in data:
            session.add(TypeDocumentIdentification(id=id, name=name, code=code))
        session.commit()
    
    # Tipos de organización
    if session.query(TypeOrganization).count() == 0:
        data = [
            (1, "Persona Jurídica y asimiladas", "1"),
            (2, "Persona Natural y asimiladas", "2"),
        ]
        for id, name, code in data:
            session.add(TypeOrganization(id=id, name=name, code=code))
        session.commit()
    
    # Tipos de régimen
    if session.query(TypeRegime).count() == 0:
        data = [
            (1, "Responsable de IVA", "48"),
            (2, "No Responsable de IVA", "49"),
        ]
        for id, name, code in data:
            session.add(TypeRegime(id=id, name=name, code=code))
        session.commit()
    
    # Tipos de responsabilidad tributaria
    if session.query(TypeLiability).count() == 0:
        data = [
            (7, "Gran contribuyente", "O-13"),
            (9, "Autorretenedor", "O-15"),
            (14, "Agente de retención en el impuesto sobre las ventas", "O-23"),
            (112, "Régimen Simple de Tributación – SIMPLE", "O-47"),
            (117, "No responsable", "R-99-PN"),
        ]
        for id, name, code in data:
            session.add(TypeLiability(id=id, name=name, code=code))
        session.commit()
    
    # Departamentos
    if session.query(Department).count() == 0:
        data = [
            (1, "Amazonas", "91"), (2, "Antioquia", "05"), (3, "Arauca", "81"),
            (4, "Atlántico", "08"), (5, "Bogotá", "11"), (6, "Bolívar", "13"),
            (7, "Boyacá", "15"), (8, "Caldas", "17"), (9, "Caquetá", "18"),
            (10, "Casanare", "85"), (11, "Cauca", "19"), (12, "Cesar", "20"),
            (13, "Chocó", "27"), (14, "Córdoba", "23"), (15, "Cundinamarca", "25"),
            (16, "Guainía", "94"), (17, "Guaviare", "95"), (18, "Huila", "41"),
            (19, "La Guajira", "44"), (20, "Magdalena", "47"), (21, "Meta", "50"),
            (22, "Nariño", "52"), (23, "Norte de Santander", "54"), (24, "Putumayo", "86"),
            (25, "Quindío", "63"), (26, "Risaralda", "66"), (27, "San Andrés y Providencia", "88"),
            (28, "Santander", "68"), (29, "Sucre", "70"), (30, "Tolima", "73"),
            (31, "Valle del Cauca", "76"), (32, "Vaupés", "97"), (33, "Vichada", "99"),
        ]
        for id, name, code in data:
            session.add(Department(id=id, name=name, code=code))
        session.commit()
    
    # Municipios principales
    if session.query(Municipality).count() == 0:
        data = [
            # Bogotá
            (149, 5, "Bogotá D.C.", "11001", "12688"),
            # Antioquia
            (1, 2, "Medellín", "05001", "12601"),
            (19, 2, "Bello", "05088", "12549"),
            (47, 2, "Envigado", "05266", "12578"),
            (59, 2, "Itagüí", "05360", "12590"),
            (85, 2, "Rionegro", "05615", "12617"),
            # Atlántico
            (168, 4, "Barranquilla", "08001", "12688"),
            # Bolívar
            (211, 6, "Cartagena", "13001", "12688"),
            # Valle del Cauca
            (799, 31, "Cali", "76001", "12688"),
            (815, 31, "Palmira", "76520", "12688"),
            (805, 31, "Buenaventura", "76109", "12688"),
            # Santander
            (680, 28, "Bucaramanga", "68001", "12688"),
            (688, 28, "Floridablanca", "68276", "12688"),
            # Nariño
            (520, 22, "Pasto", "52001", "12688"),
            (533, 22, "Ipiales", "52356", "12688"),
            (541, 22, "Tumaco", "52835", "12688"),
            # Norte de Santander
            (571, 23, "Cúcuta", "54001", "12688"),
            # Risaralda
            (615, 26, "Pereira", "66001", "12688"),
            (617, 26, "Dosquebradas", "66170", "12688"),
            # Tolima
            (758, 30, "Ibagué", "73001", "12688"),
            # Cundinamarca
            (335, 15, "Soacha", "25754", "12688"),
            (312, 15, "Chía", "25175", "12688"),
            (369, 15, "Zipaquirá", "25899", "12688"),
            # Huila
            (396, 18, "Neiva", "41001", "12688"),
            # Caldas
            (276, 8, "Manizales", "17001", "12688"),
            # Quindío
            (608, 25, "Armenia", "63001", "12688"),
            # Meta
            (483, 21, "Villavicencio", "50001", "12688"),
            # Córdoba
            (321, 14, "Montería", "23001", "12688"),
            # Cesar
            (302, 12, "Valledupar", "20001", "12688"),
            # Magdalena
            (468, 20, "Santa Marta", "47001", "12688"),
            # Cauca
            (290, 11, "Popayán", "19001", "12688"),
            # Boyacá
            (252, 7, "Tunja", "15001", "12688"),
            (260, 7, "Duitama", "15238", "12688"),
            (264, 7, "Sogamoso", "15759", "12688"),
            # Caquetá
            (295, 9, "Florencia", "18001", "12688"),
            # La Guajira
            (443, 19, "Riohacha", "44001", "12688"),
            # Sucre
            (726, 29, "Sincelejo", "70001", "12688"),
            # Arauca
            (156, 3, "Arauca", "81001", "12688"),
            # Casanare
            (298, 10, "Yopal", "85001", "12688"),
            # Putumayo
            (600, 24, "Mocoa", "86001", "12688"),
            # Amazonas
            (150, 1, "Leticia", "91001", "12688"),
            # Chocó
            (308, 13, "Quibdó", "27001", "12688"),
        ]
        for id, dept_id, name, code, codefact in data:
            session.add(Municipality(id=id, department_id=dept_id, name=name, code=code, codefacturador=codefact))
        session.commit()


def get_session():
    """Obtener sesión de base de datos"""
    return SessionLocal()
