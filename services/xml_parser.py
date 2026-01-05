"""Parser de XMLs de Siigo"""
import xml.etree.ElementTree as ET
from typing import Optional


class SiigoXmlParser:
    """Parser para archivos XML generados por Siigo"""
    
    def __init__(self):
        self.global_data = {}
        self.detail_data = []
        self.payment_data = []
        self.company_data = {}
        self.customer_data = {}
    
    def parse_file(self, file_path: str) -> Optional[dict]:
        """Parsear archivo XML de Siigo"""
        try:
            # Intentar diferentes codificaciones
            xml_content = None
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        xml_content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if xml_content is None:
                # Último intento: leer como bytes y decodificar ignorando errores
                with open(file_path, 'rb') as f:
                    raw_content = f.read()
                xml_content = raw_content.decode('utf-8', errors='replace')
            
            return self.parse(xml_content, file_path)
        except Exception as e:
            print(f"Error parsing XML file: {e}")
            return None
    
    def parse(self, xml_content: str, filename: str = "") -> Optional[dict]:
        """Parsear contenido XML de Siigo"""
        try:
            # Limpiar datos anteriores
            self.global_data = {}
            self.detail_data = []
            self.payment_data = []
            self.company_data = {}
            self.customer_data = {}
            
            root = ET.fromstring(xml_content)
            
            # Parsear datos de empresa
            self._parse_company_data(root)
            
            # Parsear datos de cliente
            self._parse_customer_data(root)
            
            # Parsear datos globales (Billing/Global/D)
            self._parse_global_data(root)
            
            # Parsear detalle (Billing/Detail/R/D)
            self._parse_detail_data(root)
            
            # Parsear pagos (Billing/Payments/R/D)
            self._parse_payment_data(root)
            
            # Construir documento
            return self._build_document_data(xml_content, filename)
            
        except Exception as e:
            print(f"Error parsing XML: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_company_data(self, root):
        """Parsear datos de la empresa emisora"""
        company = root.find('CompanyData')
        if company is not None:
            self.company_data = {
                'nit': self._get_text(company, 'Nit'),
                'name': self._get_text(company, 'Name'),
                'address': self._get_text(company, 'Address'),
                'phone': self._get_text(company, 'Phone'),
                'email': self._get_text(company, 'EMail'),
                'city_code': self._get_text(company, 'City'),
                'regime_type': self._get_text(company, 'RegimeType'),
            }
    
    def _parse_customer_data(self, root):
        """Parsear datos del cliente"""
        customer = root.find('Customer')
        if customer is not None:
            is_social_reason = self._get_text(customer, 'IsSocialReason').upper() == 'TRUE'
            
            if is_social_reason:
                name = self._get_text(customer, 'FirstName')
            else:
                first_name = self._get_text(customer, 'FirstName')
                last_name = self._get_text(customer, 'LastName')
                name = f"{first_name} {last_name}".strip()
            
            self.customer_data = {
                'identification_number': self._get_text(customer, 'Code'),
                'dv': self._get_text(customer, 'CheckDigit'),
                'name': name,
                'address': self._get_text(customer, 'Address'),
                'phone': self._get_text(customer, 'Phone'),
                'email': self._get_text(customer, 'EMail'),
            }
    
    def _parse_global_data(self, root):
        """Parsear datos globales del documento"""
        billing = root.find('Billing')
        if billing is not None:
            global_elem = billing.find('Global')
            if global_elem is not None:
                for d in global_elem.findall('D'):
                    key = d.get('K', '')
                    value = d.text or ''
                    if key:
                        self.global_data[key] = value
    
    def _parse_detail_data(self, root):
        """Parsear líneas de detalle"""
        billing = root.find('Billing')
        if billing is not None:
            detail = billing.find('Detail')
            if detail is not None:
                for row in detail.findall('R'):
                    item = {}
                    for d in row.findall('D'):
                        key = d.get('K', '')
                        value = d.text or ''
                        if key:
                            item[key] = value
                    if item:
                        self.detail_data.append(item)
    
    def _parse_payment_data(self, root):
        """Parsear datos de pago"""
        billing = root.find('Billing')
        if billing is not None:
            payments = billing.find('Payments')
            if payments is not None:
                for row in payments.findall('R'):
                    payment = {}
                    for d in row.findall('D'):
                        key = d.get('K', '')
                        value = d.text or ''
                        if key:
                            payment[key] = value
                    if payment:
                        self.payment_data.append(payment)
    
    def _build_document_data(self, xml_content: str, filename: str) -> dict:
        """Construir datos del documento"""
        document_type = self._determine_document_type()
        lines = self._build_invoice_lines()
        
        # Calcular totales desde las líneas
        # 0041 = subtotal de línea (base imponible, SIN IVA)
        # 0527 = IVA/INC de la línea
        subtotal = 0
        total_tax = 0
        
        for line in lines:
            subtotal += float(line.get('total', 0))
            total_tax += float(line.get('tax_amount', 0))
        
        # Usar el total del XML (0067) como referencia principal
        # El campo 0060 puede contener descuentos, pero a veces tiene otros valores
        xml_total = float(self._get_global('0067') or 0)
        
        # Calcular el descuento real comparando con el total del XML
        # total_xml = subtotal + tax - descuento
        # descuento = subtotal + tax - total_xml
        calculated_total = subtotal + total_tax
        if xml_total > 0 and abs(calculated_total - xml_total) > 0.01:
            # Hay descuento real
            total_discount = calculated_total - xml_total
            if total_discount < 0:
                total_discount = 0  # No puede ser negativo
        else:
            total_discount = 0
        
        total = xml_total if xml_total > 0 else calculated_total
        
        # Usar el prefijo de la resolución (0073) o el del documento (0009)
        prefix = self._get_global('0073') or self._get_global('0009') or ''
        number = self._get_global('0008') or ''
        
        return {
            'type': document_type,
            'type_document_id': self._get_type_document_id(document_type),
            'prefix': prefix,
            'number': number,
            'full_number': f"{prefix}{number}",
            'invoice_number': number,
            
            # Empresa emisora
            'company': self.company_data,
            
            # Cliente
            'customer': self.customer_data,
            
            # Resolución
            'resolution': {
                'number': self._get_global('0071'),
                'date': self._format_date(self._get_global('0072')),
                'prefix': prefix,
                'from': int(self._get_global('0074') or 0),
                'to': int(self._get_global('0075') or 0),
            },
            
            # Fechas
            'issue_date': self._format_date(self._get_global('0022')),
            'due_date': self._format_date(self._get_global('0029')),
            
            # Montos
            'subtotal': subtotal,
            'total_tax': total_tax,
            'total_discount': total_discount,
            'total': total,
            
            # Líneas de detalle
            'lines': lines,
            
            # Pagos
            'payment': self._build_payment_info(),
            
            # XML original
            'xml_content': xml_content,
            'xml_filename': filename.split('/')[-1].split('\\')[-1] if filename else '',
        }
    
    def _determine_document_type(self) -> str:
        """Determinar tipo de documento"""
        doc_type = self._get_global('0497').upper()
        
        if 'CREDITO' in doc_type or 'NC' in doc_type:
            return 'credit_note'
        elif 'DEBITO' in doc_type or 'ND' in doc_type:
            return 'debit_note'
        return 'invoice'
    
    def _get_type_document_id(self, doc_type: str) -> int:
        """Obtener ID de tipo de documento"""
        if doc_type == 'credit_note':
            return 4
        elif doc_type == 'debit_note':
            return 5
        return 1
    
    def _build_invoice_lines(self) -> list:
        """Construir líneas de factura"""
        lines = []
        
        for item in self.detail_data:
            # Obtener valores de impuestos
            tax_percent = float(item.get('0036', 0) or 0)  # Porcentaje IVA
            tax_amount = float(item.get('0527', 0) or 0)   # Monto IVA
            
            # Verificar si hay INC adicional (campos 0516=monto, 1139=porcentaje)
            inc_amount = float(item.get('0516', 0) or 0)
            inc_percent = float(item.get('1139', 0) or 0)
            
            # Determinar tipo de impuesto basado en los valores reales
            if inc_amount > 0 or inc_percent > 0:
                # Tiene INC (Impuesto Nacional al Consumo)
                tax_id = 4
                tax_amount = inc_amount
                tax_percent = inc_percent
            elif tax_percent > 0 or tax_amount > 0:
                # Tiene IVA
                tax_id = 1
            else:
                # Excluido (0% sin impuesto)
                tax_id = 1
                tax_percent = 0
                tax_amount = 0
            
            lines.append({
                'code': item.get('0031', ''),
                'description': item.get('0033', '') or item.get('0034', ''),
                'unit': item.get('0035', 'UN'),
                'quantity': float(item.get('0038', 1) or 1),
                'unit_price': float(item.get('0039', 0) or 0),
                'total': float(item.get('0041', 0) or 0),
                'tax_id': tax_id,
                'tax_percent': tax_percent,
                'tax_amount': tax_amount,
            })
        
        return lines
    
    def _build_payment_info(self) -> dict:
        """Construir información de pago"""
        payment = self.payment_data[0] if self.payment_data else {}
        
        # Código de forma de pago de Siigo (campo 0045)
        siigo_payment_code = payment.get('0045', '0080').strip()
        
        # Mapeo de códigos de Siigo a DIAN
        # payment_form_id: 1=Contado, 2=Crédito
        # payment_method_id: 10=Efectivo, 48=Tarjeta Crédito, 49=Tarjeta Débito, etc.
        payment_mapping = {
            # Contado
            '0080': {'form': 1, 'method': 10, 'name': 'Contado'},           # CONTADO CLIENTES
            '0090': {'form': 1, 'method': 10, 'name': 'Contado'},           # CONTADO PROVEEDORES
            # Crédito
            '0001': {'form': 2, 'method': 10, 'name': 'Crédito'},           # CREDITO CLIENTES NACIONALES
            '0020': {'form': 2, 'method': 10, 'name': 'Crédito'},           # CREDITO PROVEEDORES NACIONALES
            # Tarjetas
            '0010': {'form': 1, 'method': 48, 'name': 'Tarjeta Visa'},      # TARJETA VISA
            '0011': {'form': 1, 'method': 48, 'name': 'Tarjeta Amex'},      # TARJETA AMERICAN EXP
            '0012': {'form': 1, 'method': 48, 'name': 'Tarjeta Mastercard'},# TARJETA MASTERCARD
            # Anticipos
            '0040': {'form': 1, 'method': 10, 'name': 'Anticipo'},          # ANTICIPO CLIENTES
            '0060': {'form': 1, 'method': 10, 'name': 'Anticipo'},          # ANTICIPO PROVEEDORES
        }
        
        # Obtener mapeo o usar valores por defecto (Contado/Efectivo)
        mapping = payment_mapping.get(siigo_payment_code, {'form': 1, 'method': 10, 'name': 'Contado'})
        
        # Nombre de la forma de pago desde el XML (campo 0046) o del mapeo
        payment_name = payment.get('0046', mapping['name']).strip()
        
        return {
            'payment_form_id': mapping['form'],
            'payment_method_id': mapping['method'],
            'payment_name': payment_name,
            'siigo_code': siigo_payment_code,
            'payment_due_date': self._format_date(payment.get('0051', '')),
            'duration_measure': int(payment.get('1186', 0) or 0),
        }
    
    def _get_global(self, key: str) -> str:
        """Obtener valor global"""
        return self.global_data.get(key, '')
    
    def _get_text(self, element, tag: str) -> str:
        """Obtener texto de un elemento"""
        child = element.find(tag)
        return child.text if child is not None and child.text else ''
    
    def _format_date(self, date: str) -> Optional[str]:
        """Formatear fecha YYYYMMDD a YYYY-MM-DD"""
        if not date or len(date) < 8:
            return None
        return f"{date[:4]}-{date[4:6]}-{date[6:8]}"
