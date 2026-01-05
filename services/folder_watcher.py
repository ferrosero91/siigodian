"""Servicio de monitoreo de carpeta de XMLs"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from database import get_session, Document, Settings
from services.xml_parser import SiigoXmlParser


class FolderWatcherService:
    """Monitorea carpeta de XMLs de Siigo"""
    
    def __init__(self):
        session = get_session()
        settings = session.query(Settings).first()
        session.close()
        
        self.watch_folder = settings.watch_folder if settings else ""
        self.processed_folder = settings.processed_folder if settings else ""
        self.parser = SiigoXmlParser()
    
    def scan(self) -> dict:
        """Escanear carpeta y procesar XMLs"""
        results = {"processed": 0, "errors": 0, "skipped": 0}
        
        if not self.watch_folder or not os.path.exists(self.watch_folder):
            return results
        
        # Crear carpeta de procesados si no existe
        if self.processed_folder:
            Path(self.processed_folder).mkdir(parents=True, exist_ok=True)
        
        # Buscar archivos XML
        for filename in os.listdir(self.watch_folder):
            if not filename.lower().endswith('.xml'):
                continue
            
            file_path = os.path.join(self.watch_folder, filename)
            
            # Verificar si ya fue procesado
            session = get_session()
            existing = session.query(Document).filter_by(xml_filename=filename).first()
            session.close()
            
            if existing:
                results["skipped"] += 1
                continue
            
            # Parsear XML
            try:
                data = self.parser.parse_file(file_path)
                if not data:
                    results["errors"] += 1
                    continue
                
                # Crear documento
                self._create_document(data, filename)
                results["processed"] += 1
                
                # Mover a procesados
                if self.processed_folder:
                    dest = os.path.join(self.processed_folder, filename)
                    shutil.move(file_path, dest)
                    
            except Exception as e:
                print(f"Error procesando {filename}: {e}")
                results["errors"] += 1
        
        return results
    
    def _create_document(self, data: dict, filename: str):
        """Crear documento en la base de datos"""
        session = get_session()
        
        # Extraer datos
        customer = data.get("customer", {})
        
        prefix = data.get("prefix", "")
        number = data.get("number", "") or data.get("invoice_number", "")
        doc_type = data.get("type", "invoice")
        type_document_id = data.get("type_document_id", 1)
        
        # Parsear fecha
        issue_date = None
        if data.get("issue_date"):
            try:
                issue_date = datetime.strptime(data["issue_date"], "%Y-%m-%d")
            except:
                issue_date = datetime.now()
        else:
            issue_date = datetime.now()
        
        document = Document(
            type=doc_type,
            type_document_id=type_document_id,
            prefix=prefix,
            number=number,
            full_number=data.get("full_number", f"{prefix}{number}"),
            issue_date=issue_date,
            customer_nit=customer.get("identification_number", ""),
            customer_name=customer.get("name", ""),
            customer_email=customer.get("email", ""),
            subtotal=data.get("subtotal", 0),
            total_tax=data.get("total_tax", 0),
            total_discount=data.get("total_discount", 0),
            total=data.get("total", 0),
            status="pending",
            xml_content=data.get("xml_content", ""),
            xml_filename=filename,
            parsed_data=data,
        )
        
        session.add(document)
        session.commit()
        session.close()
