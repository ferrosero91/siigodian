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
    
    # Departamentos y Municipios - importar desde CSV si están vacíos
    if session.query(Department).count() == 0 or session.query(Municipality).count() == 0:
        _import_geo_catalogs(session)


def _import_geo_catalogs(session):
    """Importar departamentos y municipios desde CSV"""
    import os
    
    # Buscar CSV en data/csv del proyecto
    csv_path = os.path.join(os.path.dirname(__file__), 'data', 'csv')
    
    def read_csv(filename):
        filepath = os.path.join(csv_path, filename)
        if not os.path.exists(filepath):
            return []
        data = []
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data.append(line.split('\t'))
                break
            except UnicodeDecodeError:
                continue
        return data
    
    # Limpiar tablas (municipios primero por FK)
    session.query(Municipality).delete()
    session.query(Department).delete()
    session.commit()
    
    # Importar departamentos
    dept_data = read_csv('departments.csv')
    if dept_data:
        for row in dept_data:
            if len(row) >= 3:
                session.add(Department(id=int(row[0]), name=row[2], code=row[3] if len(row) > 3 else str(row[0])))
        session.commit()
        print(f"Importados {session.query(Department).count()} departamentos desde CSV")
    
    # Importar municipios
    muni_data = read_csv('municipalities.csv')
    if muni_data:
        for row in muni_data:
            if len(row) >= 4:
                session.add(Municipality(
                    id=int(row[0]), department_id=int(row[1]), name=row[2].strip(),
                    code=row[3], codefacturador=row[4] if len(row) > 4 else None
                ))
        session.commit()
        print(f"Importados {session.query(Municipality).count()} municipios desde CSV")


def get_session():
    """Obtener sesión de base de datos"""
    return SessionLocal()
