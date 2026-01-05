"""Servicio de comunicación con ApiDian"""
import requests
from datetime import datetime
from typing import Optional
from database import get_session, Settings, Document, Resolution


class ApiDianService:
    """Cliente para la API de facturación electrónica"""
    
    def __init__(self):
        session = get_session()
        self.settings = session.query(Settings).first()
        session.close()
        
        self.base_url = self.settings.api_url.rstrip('/') if self.settings else ""
        self.headers = self._get_headers()
    
    def _get_headers(self) -> dict:
        """Obtener headers para las peticiones"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.settings and self.settings.api_token:
            headers["Authorization"] = f"Bearer {self.settings.api_token}"
        return headers
    
    def _post(self, url: str, data: dict) -> dict:
        """Realizar petición POST"""
        try:
            response = requests.post(url, json=data, headers=self.headers, timeout=60)
            
            try:
                result = response.json() if response.text else {}
            except:
                result = {"raw_response": response.text}
            
            result["success"] = response.status_code in [200, 201]
            if not result["success"]:
                # Intentar extraer mensaje de error más específico
                if "errors" in result:
                    errors = result["errors"]
                    if isinstance(errors, dict):
                        msgs = []
                        for key, val in errors.items():
                            if isinstance(val, list):
                                msgs.append(f"{key}: {', '.join(val)}")
                            else:
                                msgs.append(f"{key}: {val}")
                        result["message"] = "; ".join(msgs)
                    else:
                        result["message"] = str(errors)
                elif "message" not in result:
                    result["message"] = f"Error HTTP {response.status_code}: {response.text[:200]}"
            return result
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _put(self, url: str, data: dict) -> dict:
        """Realizar petición PUT"""
        try:
            response = requests.put(url, json=data, headers=self.headers, timeout=60)
            try:
                result = response.json() if response.text else {}
            except:
                result = {"raw_response": response.text}
            result["success"] = response.status_code in [200, 201]
            if not result["success"] and "message" not in result:
                result["message"] = result.get("error", response.text[:200] if response.text else "Error desconocido")
            return result
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _get(self, url: str) -> dict:
        """Realizar petición GET"""
        try:
            response = requests.get(url, headers=self.headers, timeout=60)
            return {"success": response.ok, "content": response.content, "status": response.status_code}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _get_json(self, url: str) -> dict:
        """Realizar petición GET y devolver JSON"""
        try:
            response = requests.get(url, headers=self.headers, timeout=60)
            try:
                result = response.json() if response.text else {}
            except:
                result = {"raw_response": response.text}
            result["success"] = response.status_code in [200, 201]
            return result
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def get_acquirer(self, document_type_id: int, document_number: str) -> dict:
        """Consultar tercero en la DIAN por tipo y número de documento
        
        IMPORTANTE: La DIAN espera el CÓDIGO del tipo de documento (ej: 13 para CC),
        no el ID de la tabla (ej: 3 para CC). Este método convierte automáticamente.
        """
        # Convertir ID de tipo de documento al CÓDIGO que espera la DIAN
        session = get_session()
        from database import TypeDocumentIdentification
        type_doc = session.query(TypeDocumentIdentification).get(document_type_id)
        session.close()
        
        if type_doc and type_doc.code:
            document_type_code = type_doc.code
        else:
            # Si no se encuentra, usar el ID como código (fallback)
            document_type_code = str(document_type_id)
        
        url = f"{self.base_url}/customer/{document_type_code}/{document_number}"
        result = self._get_json(url)
        
        # Debug: imprimir respuesta completa
        import json
        print(f"[GetAcquirer] URL: {url}")
        print(f"[GetAcquirer] Response: {json.dumps(result, indent=2, default=str)}")
        
        if result.get("success"):
            # La estructura es: ResponseDian (que ya es Body) -> GetAcquirerResponse -> GetAcquirerResult
            response_dian = result.get("ResponseDian", {})
            
            # ResponseDian ya contiene Body directamente (ver CustomerController.php línea 98)
            acquirer_response = response_dian.get("GetAcquirerResponse", {})
            acquirer_result = acquirer_response.get("GetAcquirerResult", {})
            
            print(f"[GetAcquirer] acquirer_result: {json.dumps(acquirer_result, indent=2, default=str)}")
            
            if acquirer_result:
                # Campos de la respuesta DIAN:
                # - ReceiverName: nombre del tercero
                # - ReceiverEmail: email del tercero
                # - StatusCode: código de estado (200 = OK)
                
                name = ""
                email = ""
                
                # Obtener nombre - la DIAN usa ReceiverName
                name = acquirer_result.get("ReceiverName", "") or acquirer_result.get("Name", "") or acquirer_result.get("BusinessName", "")
                
                # Si no hay nombre directo, intentar con nombre compuesto
                if not name:
                    first_name = acquirer_result.get("FirstName", "")
                    second_name = acquirer_result.get("SecondName", "")
                    first_surname = acquirer_result.get("FirstSurname", "") or acquirer_result.get("FamilyName", "")
                    second_surname = acquirer_result.get("SecondSurname", "")
                    if first_name or first_surname:
                        parts = [first_name, second_name, first_surname, second_surname]
                        name = " ".join(p for p in parts if p).strip()
                
                # Obtener email - la DIAN usa ReceiverEmail
                email = acquirer_result.get("ReceiverEmail", "") or acquirer_result.get("Email", "") or acquirer_result.get("ElectronicMail", "")
                
                print(f"[GetAcquirer] Extracted - name: {name}, email: {email}")
                
                return {
                    "success": True,
                    "name": name,
                    "email": email,
                    "data": acquirer_result,
                }
            else:
                # Si no hay acquirer_result, puede que la estructura sea diferente
                # Intentar buscar en otros lugares
                print(f"[GetAcquirer] No acquirer_result found, checking alternative structures")
                return {
                    "success": False,
                    "message": result.get("message", "No se encontró información del tercero"),
                    "raw": response_dian,
                }
        
        return result
    
    def test_connection(self) -> dict:
        """Probar conexión con la API"""
        url = f"{self.base_url}/plan/infoplanuser"
        return self._get(url)
    
    def configure_company(self) -> dict:
        """Configurar empresa en ApiDian"""
        url = f"{self.base_url}/config/{self.settings.company_nit}/{self.settings.company_dv}"
        data = {
            "type_document_identification_id": self.settings.type_document_identification_id,
            "type_organization_id": self.settings.type_organization_id,
            "type_regime_id": self.settings.type_regime_id,
            "type_liability_id": self.settings.type_liability_id,
            "business_name": self.settings.company_name,
            "merchant_registration": self.settings.merchant_registration or "0000000-00",
            "municipality_id": self.settings.municipality_id,
            "address": self.settings.company_address,
            "phone": self.settings.company_phone,
            "email": self.settings.company_email,
            "mail_host": self.settings.mail_host,
            "mail_port": str(self.settings.mail_port or 587),
            "mail_username": self.settings.mail_username,
            "mail_password": self.settings.mail_password,
            "mail_encryption": self.settings.mail_encryption or "tls",
        }
        return self._post(url, data)
    
    def configure_software(self) -> dict:
        """Configurar software de facturación en ApiDian"""
        url = f"{self.base_url}/config/software"
        data = {
            "id": self.settings.software_id,
            "pin": int(self.settings.software_pin),
        }
        return self._put(url, data)
    
    def configure_software_ds(self) -> dict:
        """Configurar software de Documento Soporte en ApiDian"""
        ds_software_id = getattr(self.settings, 'ds_software_id', None)
        ds_software_pin = getattr(self.settings, 'ds_software_pin', None)
        
        if not ds_software_id or not ds_software_pin:
            return {"success": False, "message": "Configure el Software ID y PIN de Documento Soporte"}
        
        # El endpoint para DS es el mismo pero con type_document_id=11
        url = f"{self.base_url}/config/software"
        data = {
            "id": ds_software_id,
            "pin": int(ds_software_pin),
        }
        return self._put(url, data)
    
    def configure_resolution(self, resolution: Resolution) -> dict:
        """Configurar resolución en ApiDian"""
        url = f"{self.base_url}/config/resolution"
        data = {
            "type_document_id": resolution.type_document_id,
            "prefix": resolution.prefix,
            "resolution": resolution.resolution,
            "resolution_date": resolution.resolution_date.strftime("%Y-%m-%d") if resolution.resolution_date else "",
            "technical_key": resolution.technical_key or "fc8eac422eba16e22ffd8c6f94b3f40a6e38162c",
            "from": resolution.from_number,
            "to": resolution.to_number,
            "date_from": resolution.date_from.strftime("%Y-%m-%d") if resolution.date_from else "",
            "date_to": resolution.date_to.strftime("%Y-%m-%d") if resolution.date_to else "",
        }
        return self._put(url, data)
    
    def send_invoice(self, document: Document) -> dict:
        """Enviar factura a la DIAN"""
        endpoint = self._get_invoice_endpoint()
        data = self._build_invoice_payload(document)
        
        # Guardar request
        session = get_session()
        document.api_request = data
        session.merge(document)
        session.commit()
        session.close()
        
        result = self._post(endpoint, data)
        self._process_response(document, result)
        return result
    
    def send_credit_note(self, document: Document) -> dict:
        """Enviar nota crédito a la DIAN"""
        endpoint = self._get_credit_note_endpoint()
        data = self._build_credit_note_payload(document)
        
        session = get_session()
        document.api_request = data
        session.merge(document)
        session.commit()
        session.close()
        
        result = self._post(endpoint, data)
        self._process_response(document, result)
        return result
    
    def send_debit_note(self, document: Document) -> dict:
        """Enviar nota débito a la DIAN"""
        endpoint = self._get_debit_note_endpoint()
        data = self._build_debit_note_payload(document)
        
        session = get_session()
        document.api_request = data
        session.merge(document)
        session.commit()
        session.close()
        
        result = self._post(endpoint, data)
        self._process_response(document, result)
        return result
    
    def send_support_document(self, document: Document) -> dict:
        """Enviar documento soporte a la DIAN"""
        # Verificar configuración de DS
        ds_software_id = getattr(self.settings, 'ds_software_id', None)
        ds_software_pin = getattr(self.settings, 'ds_software_pin', None)
        ds_test_set_id = getattr(self.settings, 'ds_test_set_id', None)
        
        if not ds_software_id or not ds_software_pin:
            return {
                "success": False,
                "message": "Configure el Software ID y PIN de Documento Soporte en Configuración > API DIAN"
            }
        
        # Validar configuración en ambiente de habilitación
        if self.settings.type_environment_id == 2:
            if not ds_test_set_id:
                return {
                    "success": False,
                    "message": "Configure el TestSetId de Documento Soporte en Configuración > API DIAN > Documento Soporte Electrónico"
                }
        
        # Configurar software de DS antes de enviar
        config_result = self.configure_software_ds()
        # Log del resultado de configuración
        print(f"[DS] Config software result: {config_result}")
        
        endpoint = self._get_support_document_endpoint()
        data = self._build_support_document_payload(document)
        
        # Log del payload para debug
        import json
        print(f"[DS] Endpoint: {endpoint}")
        print(f"[DS] Payload: {json.dumps(data, indent=2, default=str)}")
        
        session = get_session()
        document.api_request = data
        session.merge(document)
        session.commit()
        session.close()
        
        result = self._post(endpoint, data)
        
        # Log del resultado
        print(f"[DS] Result: {json.dumps(result, indent=2, default=str)}")
        
        self._process_response(document, result)
        return result
    
    def send_sd_adjustment_note(self, document: Document) -> dict:
        """Enviar nota de ajuste a documento soporte a la DIAN"""
        # Configurar software de DS antes de enviar (igual que en send_support_document)
        ds_software_id = getattr(self.settings, 'ds_software_id', None)
        ds_software_pin = getattr(self.settings, 'ds_software_pin', None)
        
        if ds_software_id and ds_software_pin:
            config_result = self.configure_software_ds()
            print(f"[NA-DS] Config software result: {config_result}")
        
        endpoint = self._get_sd_adjustment_note_endpoint()
        data = self._build_sd_adjustment_note_payload(document)
        
        # Log del payload para debug
        import json
        print(f"[NA-DS] Endpoint: {endpoint}")
        print(f"[NA-DS] Payload: {json.dumps(data, indent=2, default=str)}")
        
        session = get_session()
        document.api_request = data
        session.merge(document)
        session.commit()
        session.close()
        
        result = self._post(endpoint, data)
        
        # Log del resultado
        print(f"[NA-DS] Result: {json.dumps(result, indent=2, default=str)}")
        
        self._process_response(document, result)
        return result
    
    def _get_invoice_endpoint(self) -> str:
        if self.settings.type_environment_id == 2 and self.settings.test_set_id:
            return f"{self.base_url}/invoice/{self.settings.test_set_id}"
        return f"{self.base_url}/invoice"
    
    def _get_credit_note_endpoint(self) -> str:
        if self.settings.type_environment_id == 2 and self.settings.test_set_id:
            return f"{self.base_url}/credit-note/{self.settings.test_set_id}"
        return f"{self.base_url}/credit-note"
    
    def _get_debit_note_endpoint(self) -> str:
        if self.settings.type_environment_id == 2 and self.settings.test_set_id:
            return f"{self.base_url}/debit-note/{self.settings.test_set_id}"
        return f"{self.base_url}/debit-note"
    
    def _get_support_document_endpoint(self) -> str:
        # Documento Soporte usa su propio test_set_id (ds_test_set_id)
        ds_test_set_id = getattr(self.settings, 'ds_test_set_id', None)
        if self.settings.type_environment_id == 2 and ds_test_set_id:
            return f"{self.base_url}/support-document/{ds_test_set_id}"
        return f"{self.base_url}/support-document"
    
    def _get_sd_adjustment_note_endpoint(self) -> str:
        # Nota de Ajuste a DS usa el mismo test_set_id que DS
        ds_test_set_id = getattr(self.settings, 'ds_test_set_id', None)
        if self.settings.type_environment_id == 2 and ds_test_set_id:
            return f"{self.base_url}/sd-credit-note/{ds_test_set_id}"
        return f"{self.base_url}/sd-credit-note"
    
    def _build_invoice_payload(self, document: Document) -> dict:
        """Construir payload para factura"""
        parsed = document.parsed_data or {}
        now = datetime.now()
        
        return {
            "number": int(document.number),
            "type_document_id": document.type_document_id or 1,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "prefix": document.prefix,
            "sendmail": True,
            "customer": self._build_customer(parsed.get("customer", {})),
            "payment_form": self._build_payment(parsed.get("payment", {})),
            "legal_monetary_totals": self._build_totals(parsed),
            "tax_totals": self._build_taxes(parsed),
            "invoice_lines": self._build_lines(parsed.get("lines", [])),
        }
    
    def _build_credit_note_payload(self, document: Document) -> dict:
        """Construir payload para nota crédito"""
        parsed = document.parsed_data or {}
        now = datetime.now()
        
        # Obtener factura de referencia
        session = get_session()
        ref_doc = session.query(Document).get(document.reference_document_id) if document.reference_document_id else None
        session.close()
        
        return {
            "number": int(document.number),
            "type_document_id": 4,
            "prefix": document.prefix,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "sendmail": True,
            "notes": parsed.get("discrepancy_description", "Nota crédito"),
            "billing_reference": {
                "number": ref_doc.full_number if ref_doc else "",
                "uuid": document.reference_cufe or "",
                "issue_date": ref_doc.issue_date.strftime("%Y-%m-%d") if ref_doc and ref_doc.issue_date else now.strftime("%Y-%m-%d"),
            },
            "discrepancyresponsecode": int(parsed.get("discrepancy_code", 2)),
            "discrepancyresponsedescription": parsed.get("discrepancy_description", "Anulación"),
            "customer": self._build_customer(parsed.get("customer", {})),
            "legal_monetary_totals": self._build_totals(parsed),
            "tax_totals": self._build_taxes(parsed),
            "credit_note_lines": self._build_lines(parsed.get("lines", [])),
        }
    
    def _build_debit_note_payload(self, document: Document) -> dict:
        """Construir payload para nota débito"""
        parsed = document.parsed_data or {}
        now = datetime.now()
        
        session = get_session()
        ref_doc = session.query(Document).get(document.reference_document_id) if document.reference_document_id else None
        session.close()
        
        return {
            "number": int(document.number),
            "type_document_id": 5,
            "prefix": document.prefix,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "sendmail": True,
            "notes": parsed.get("discrepancy_description", "Nota débito"),
            "billing_reference": {
                "number": ref_doc.full_number if ref_doc else "",
                "uuid": document.reference_cufe or "",
                "issue_date": ref_doc.issue_date.strftime("%Y-%m-%d") if ref_doc and ref_doc.issue_date else now.strftime("%Y-%m-%d"),
            },
            "discrepancyresponsecode": int(parsed.get("discrepancy_code", 3)),
            "discrepancyresponsedescription": parsed.get("discrepancy_description", "Ajuste"),
            "customer": self._build_customer(parsed.get("customer", {})),
            "requested_monetary_totals": self._build_totals(parsed),
            "tax_totals": self._build_taxes(parsed),
            "debit_note_lines": self._build_lines(parsed.get("lines", [])),
        }
    
    def _build_support_document_payload(self, document: Document) -> dict:
        """Construir payload para documento soporte (type_document_id=11)
        Formato exacto según POS DianSupportDocumentService.php
        """
        parsed = document.parsed_data or {}
        now = datetime.now()
        lines = parsed.get("lines", [])
        
        # Obtener resolución para el resolution_number
        session = get_session()
        resolution = session.query(Resolution).filter(
            Resolution.type_document_id == 11,
            Resolution.prefix == document.prefix,
            Resolution.is_active == True
        ).first()
        resolution_number = resolution.resolution if resolution else ""
        session.close()
        
        # Calcular totales - IGUAL QUE EN EL POS
        # El unit_price del formulario se asume que INCLUYE IVA (como en una compra real)
        line_extension_amount = 0
        total_tax_amount = 0
        
        for line in lines:
            tax_rate = float(line.get("tax_percent", 0))
            quantity = float(line.get("quantity", 1))
            unit_cost = float(line.get("unit_price", 0))
            
            # Precio unitario sin IVA (el precio ingresado incluye IVA)
            if tax_rate > 0:
                unit_price_without_tax = unit_cost / (1 + (tax_rate / 100))
            else:
                unit_price_without_tax = unit_cost
            
            # Subtotal = cantidad × precio sin IVA
            subtotal = quantity * unit_price_without_tax
            tax_amount = subtotal * (tax_rate / 100)
            
            line_extension_amount += subtotal
            total_tax_amount += tax_amount
        
        tax_inclusive_amount = line_extension_amount + total_tax_amount
        
        return {
            "number": int(document.number),
            "type_document_id": 11,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "notes": parsed.get("notes", "SIN OBSERVACIONES"),
            "sendmail": False,
            "sendmailtome": False,
            "resolution_number": resolution_number,
            "prefix": document.prefix,
            "establishment_name": self.settings.company_name or "EMPRESA",
            "seller": self._build_seller(parsed.get("customer", {})),
            "payment_form": {
                "payment_form_id": 1,
                "payment_method_id": 10,
                "payment_due_date": now.strftime("%Y-%m-%d"),
                "duration_measure": "0",
            },
            "allowance_charges": [{
                "discount_id": 10,
                "charge_indicator": False,
                "allowance_charge_reason": "DESCUENTO GENERAL",
                "amount": "0.00",
                "base_amount": f"{line_extension_amount:.2f}",
            }],
            "legal_monetary_totals": {
                "line_extension_amount": f"{line_extension_amount:.2f}",
                "tax_exclusive_amount": f"{line_extension_amount:.2f}",
                "tax_inclusive_amount": f"{tax_inclusive_amount:.2f}",
                "allowance_total_amount": "0.00",
                "charge_total_amount": "0.00",
                "payable_amount": f"{tax_inclusive_amount:.2f}",
            },
            "tax_totals": self._build_ds_tax_totals(lines),
            "invoice_lines": self._build_ds_invoice_lines(lines, now.strftime("%Y-%m-%d")),
        }
    
    def _build_sd_adjustment_note_payload(self, document: Document) -> dict:
        """Construir payload para nota de ajuste a documento soporte (type_document_id=13)
        Formato exacto según POS DianSupportDocumentService.php
        """
        parsed = document.parsed_data or {}
        now = datetime.now()
        lines = parsed.get("lines", [])
        
        # Obtener documento soporte de referencia
        session = get_session()
        ref_doc = session.query(Document).get(document.reference_document_id) if document.reference_document_id else None
        session.close()
        
        # Calcular totales - IGUAL QUE EN EL POS
        line_extension_amount = 0
        total_tax_amount = 0
        
        for line in lines:
            tax_rate = float(line.get("tax_percent", 0))
            quantity = float(line.get("quantity", 1))
            unit_cost = float(line.get("unit_price", 0))
            
            # Precio unitario sin IVA
            if tax_rate > 0:
                unit_price_without_tax = unit_cost / (1 + (tax_rate / 100))
            else:
                unit_price_without_tax = unit_cost
            
            subtotal = quantity * unit_price_without_tax
            tax_amount = subtotal * (tax_rate / 100)
            
            line_extension_amount += subtotal
            total_tax_amount += tax_amount
        
        tax_inclusive_amount = line_extension_amount + total_tax_amount
        
        # Número de referencia del DS original
        ds_number = ref_doc.full_number if ref_doc else ""
        
        return {
            # billing_reference DEBE ir primero según Postman
            "billing_reference": {
                "number": ds_number,
                "uuid": document.reference_cufe or "",
                "issue_date": ref_doc.issue_date.strftime("%Y-%m-%d") if ref_doc and ref_doc.issue_date else now.strftime("%Y-%m-%d"),
            },
            "discrepancyresponsecode": int(parsed.get("discrepancy_code", 2)),
            "discrepancyresponsedescription": parsed.get("discrepancy_description", "DEVOLUCION DE MERCANCIA"),
            "notes": parsed.get("discrepancy_description", "NOTA DE AJUSTE AL DOCUMENTO SOPORTE"),
            "prefix": document.prefix,
            "number": int(document.number),
            "type_document_id": 13,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "establishment_name": self.settings.company_name or "EMPRESA",
            "sendmail": False,
            "sendmailtome": False,
            "seller": self._build_seller(parsed.get("customer", {})),
            "tax_totals": self._build_ds_tax_totals(lines),
            "allowance_charges": [{
                "discount_id": 1,
                "charge_indicator": False,
                "allowance_charge_reason": "DESCUENTO GENERAL",
                "amount": "0.00",
                "base_amount": f"{line_extension_amount:.2f}",
            }],
            "legal_monetary_totals": {
                "line_extension_amount": f"{line_extension_amount:.2f}",
                "tax_exclusive_amount": f"{line_extension_amount:.2f}",
                "tax_inclusive_amount": f"{tax_inclusive_amount:.2f}",
                "allowance_total_amount": "0.00",
                "charge_total_amount": "0.00",
                "payable_amount": f"{tax_inclusive_amount:.2f}",
            },
            "credit_note_lines": self._build_ds_credit_note_lines(lines),
        }
    
    def _build_seller(self, seller: dict) -> dict:
        """Construir datos del vendedor/proveedor para documento soporte - formato exacto POS"""
        nit = str(seller.get("identification_number", "222222222222"))
        dv = seller.get("dv") or self._calculate_dv(nit)
        
        # postal_zone_code debe ser numérico según SupportDocumentRequest.php
        postal_zone = seller.get("postal_zone_code", "110111")
        try:
            postal_zone_code = int(str(postal_zone).replace("-", ""))
        except:
            postal_zone_code = 110111
        
        return {
            "identification_number": nit,
            "dv": str(dv),
            "name": seller.get("name", "PROVEEDOR"),
            "phone": str(seller.get("phone", "0000000000")),
            "address": seller.get("address", "Sin dirección"),
            "email": seller.get("email", "sin@email.com"),
            "merchant_registration": seller.get("merchant_registration", "0000000-00"),
            "type_document_identification_id": int(seller.get("type_document_identification_id", 3)),  # CC por defecto (como Postman)
            "type_organization_id": int(seller.get("type_organization_id", 2)),  # Persona Natural
            "type_regime_id": int(seller.get("type_regime_id", 2)),  # No responsable IVA
            "type_liability_id": int(seller.get("type_liability_id", 117)),  # No responsable
            "municipality_id": int(seller.get("municipality_id", 149)),  # Bogotá por defecto
            "postal_zone_code": postal_zone_code,  # Numérico según validación ApiDian
        }
    
    def _calculate_dv(self, nit: str) -> str:
        """Calcular dígito de verificación (Algoritmo DIAN Colombia 2026)
        
        Vector de pesos: 3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71
        Se aplican de derecha a izquierda (el último dígito se multiplica por 3).
        
        Ejemplo: NIT 1085286295
        5×3 + 9×7 + 2×13 + 6×17 + 8×19 + 2×23 + 5×29 + 8×37 + 0×41 + 1×43
        = 15 + 63 + 26 + 102 + 152 + 46 + 145 + 296 + 0 + 43 = 888
        888 % 11 = 8
        11 - 8 = 3 ✓
        """
        import re
        # Limpiar el NIT (solo números)
        nit = re.sub(r'[^0-9]', '', str(nit))
        
        if not nit:
            return "0"
        
        # Pesos según DIAN - el primer peso (3) se aplica al último dígito
        weights = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
        
        # Invertir los dígitos del NIT para aplicar pesos de derecha a izquierda
        digits = list(reversed(nit))
        
        # Sumar productos de cada dígito por su peso correspondiente
        total = 0
        for i, digit in enumerate(digits):
            if i >= len(weights):
                break
            total += int(digit) * weights[i]
        
        # Calcular residuo
        remainder = total % 11
        
        # Si residuo es 0 o 1, el DV es ese valor; sino es 11 - residuo
        if remainder == 0 or remainder == 1:
            return str(remainder)
        
        return str(11 - remainder)
    
    def _build_customer(self, customer: dict) -> dict:
        return {
            "identification_number": int(customer.get("identification_number", 0)),
            "dv": int(customer.get("dv", 0)) if customer.get("dv") else None,
            "name": customer.get("name", ""),
            "phone": customer.get("phone", ""),
            "address": customer.get("address", ""),
            "email": customer.get("email", ""),
            "merchant_registration": "0000000-00",
            "type_document_identification_id": 3,
            "type_organization_id": 2,
            "type_liability_id": 117,
            "municipality_id": 1006,
            "type_regime_id": 2,
        }
    
    def _build_payment(self, payment: dict) -> dict:
        payment_form_id = payment.get("payment_form_id", 1)
        payment_method_id = payment.get("payment_method_id", 10)
        
        # Para crédito, usar la fecha de vencimiento del XML; para contado, usar fecha actual
        if payment_form_id == 2:  # Crédito
            due_date = payment.get("payment_due_date") or datetime.now().strftime("%Y-%m-%d")
            duration = str(payment.get("duration_measure", 30))  # Días de crédito
        else:  # Contado
            due_date = datetime.now().strftime("%Y-%m-%d")
            duration = "0"
        
        return {
            "payment_form_id": payment_form_id,
            "payment_method_id": payment_method_id,
            "payment_due_date": due_date,
            "duration_measure": duration,
        }
    
    def _build_ds_payment(self, payment: dict) -> dict:
        """Construir payment_form para documento soporte - formato exacto Postman"""
        return {
            "payment_form_id": 1,
            "payment_method_id": 10,
            "payment_due_date": datetime.now().strftime("%Y-%m-%d"),
            "duration_measure": "0",
        }
    
    def _build_ds_totals(self, parsed: dict) -> dict:
        """Construir totales para documento soporte - formato exacto Postman"""
        subtotal = float(parsed.get("subtotal", 0))
        total_tax = float(parsed.get("total_tax", 0))
        total = float(parsed.get("total", subtotal + total_tax))
        
        return {
            "line_extension_amount": f"{subtotal:.2f}",
            "tax_exclusive_amount": f"{subtotal:.2f}",
            "tax_inclusive_amount": f"{subtotal + total_tax:.2f}",
            "allowance_total_amount": "0.00",
            "charge_total_amount": "0.00",
            "payable_amount": f"{total:.2f}",
        }
    
    def _build_ds_taxes(self, parsed: dict) -> list:
        """Construir tax_totals para documento soporte - SIEMPRE debe tener al menos un elemento"""
        subtotal = float(parsed.get("subtotal", 0))
        total_tax = float(parsed.get("total_tax", 0))
        
        # Siempre retornar al menos un tax_total con IVA 0%
        return [{
            "tax_id": 1,
            "tax_amount": f"{total_tax:.2f}",
            "percent": "0",
            "taxable_amount": f"{subtotal:.2f}",
        }]
    
    def _build_ds_tax_totals(self, lines: list) -> list:
        """Construir tax_totals para documento soporte - formato exacto POS"""
        tax_groups = {}
        
        for line in lines:
            rate = float(line.get("tax_percent", 0))
            quantity = float(line.get("quantity", 1))
            unit_cost = float(line.get("unit_price", 0))
            
            # Precio unitario sin IVA (el precio incluye IVA)
            if rate > 0:
                unit_price_without_tax = unit_cost / (1 + (rate / 100))
            else:
                unit_price_without_tax = unit_cost
            
            # Subtotal = cantidad × precio sin IVA
            subtotal = quantity * unit_price_without_tax
            tax_amount = subtotal * (rate / 100)
            
            key = f"1_{rate}"  # IVA + tasa
            if key not in tax_groups:
                tax_groups[key] = {
                    "tax_id": 1,
                    "tax_amount": 0,
                    "taxable_amount": 0,
                    "percent": rate,
                }
            
            tax_groups[key]["tax_amount"] += tax_amount
            tax_groups[key]["taxable_amount"] += subtotal
        
        # Si no hay impuestos, agregar IVA 0%
        if not tax_groups:
            tax_groups["1_0"] = {
                "tax_id": 1,
                "tax_amount": 0,
                "taxable_amount": 0,
                "percent": 0,
            }
        
        # Formatear según POS: percent como entero string "0" no "0.00"
        result = []
        for group in tax_groups.values():
            result.append({
                "tax_id": group["tax_id"],
                "tax_amount": f"{group['tax_amount']:.2f}",
                "percent": str(int(group["percent"])),  # "0" no "0.00"
                "taxable_amount": f"{group['taxable_amount']:.2f}",
            })
        
        return result
    
    def _build_ds_invoice_lines(self, lines: list, document_date: str) -> list:
        """Construir líneas para documento soporte - formato exacto Postman"""
        result = []
        
        for line in lines:
            tax_rate = float(line.get("tax_percent", 0))
            quantity = float(line.get("quantity", 1))
            unit_cost = float(line.get("unit_price", 0))
            
            # Precio unitario sin IVA (el precio incluye IVA)
            if tax_rate > 0:
                unit_price_without_tax = unit_cost / (1 + (tax_rate / 100))
            else:
                unit_price_without_tax = unit_cost
            
            # line_extension_amount = cantidad × precio_unitario (sin IVA)
            line_extension_amount = quantity * unit_price_without_tax
            tax_amount = line_extension_amount * (tax_rate / 100)
            
            # Formato según Postman
            quantity_formatted = f"{quantity:.2f}"
            line_extension_formatted = f"{line_extension_amount:.2f}"
            price_amount_formatted = f"{unit_price_without_tax:.2f}"
            
            # En las líneas, percent va con decimales "0.00" según Postman
            result.append({
                "unit_measure_id": 70,
                "invoiced_quantity": quantity_formatted,
                "line_extension_amount": line_extension_formatted,
                "free_of_charge_indicator": False,
                "allowance_charges": [{
                    "charge_indicator": False,
                    "allowance_charge_reason": "DESCUENTO GENERAL",
                    "amount": "0.00",
                    "base_amount": line_extension_formatted,
                }],
                "tax_totals": [{
                    "tax_id": 1,
                    "tax_amount": f"{tax_amount:.2f}",
                    "percent": f"{tax_rate:.2f}",  # Con decimales en líneas
                    "taxable_amount": line_extension_formatted,
                }],
                "description": line.get("description", line.get("name", "Producto")),
                "notes": "",
                "code": str(line.get("code", "PROD")),
                "type_item_identification_id": 4,
                "price_amount": price_amount_formatted,
                "base_quantity": quantity_formatted,
                "type_generation_transmition_id": 1,
                "start_date": document_date,
            })
        
        return result
    
    def _build_ds_credit_note_lines(self, lines: list) -> list:
        """Construir líneas para nota de ajuste DS - formato exacto Postman"""
        result = []
        
        for line in lines:
            tax_rate = float(line.get("tax_percent", 0))
            quantity = float(line.get("quantity", 1))
            unit_cost = float(line.get("unit_price", 0))
            
            # Precio unitario sin IVA
            if tax_rate > 0:
                unit_price_without_tax = unit_cost / (1 + (tax_rate / 100))
            else:
                unit_price_without_tax = unit_cost
            
            line_extension_amount = quantity * unit_price_without_tax
            tax_amount = line_extension_amount * (tax_rate / 100)
            
            quantity_formatted = f"{quantity:.2f}"
            line_extension_formatted = f"{line_extension_amount:.2f}"
            price_amount_formatted = f"{unit_price_without_tax:.2f}"
            
            result.append({
                "unit_measure_id": 70,
                "invoiced_quantity": quantity_formatted,
                "line_extension_amount": line_extension_formatted,
                "free_of_charge_indicator": False,
                "allowance_charges": [{
                    "charge_indicator": False,
                    "allowance_charge_reason": "DESCUENTO GENERAL",
                    "amount": "0.00",
                    "base_amount": line_extension_formatted,
                }],
                "tax_totals": [{
                    "tax_id": 1,
                    "tax_amount": f"{tax_amount:.2f}",
                    "percent": f"{tax_rate:.2f}",  # Con decimales en líneas
                    "taxable_amount": line_extension_formatted,
                }],
                "description": line.get("description", line.get("name", "Producto")),
                "notes": "",
                "code": str(line.get("code", "PROD")),
                "type_item_identification_id": 4,
                "price_amount": price_amount_formatted,
                "base_quantity": quantity_formatted,
            })
        
        return result
    
    def _build_totals(self, parsed: dict) -> dict:
        """Construir totales monetarios para la DIAN"""
        subtotal = float(parsed.get("subtotal", 0))
        total_tax = float(parsed.get("total_tax", 0))
        total_discount = float(parsed.get("total_discount", 0))
        total = float(parsed.get("total", 0))
        
        # line_extension_amount = suma de bases imponibles (subtotal sin impuestos)
        # tax_exclusive_amount = subtotal - descuentos
        # tax_inclusive_amount = subtotal - descuentos + impuestos
        # payable_amount = total a pagar
        
        tax_exclusive = subtotal - total_discount
        tax_inclusive = tax_exclusive + total_tax
        
        # Si el total parseado es diferente, usarlo (viene del XML)
        if total > 0 and abs(total - tax_inclusive) > 0.01:
            payable = total
        else:
            payable = tax_inclusive
        
        return {
            "line_extension_amount": f"{subtotal:.2f}",
            "tax_exclusive_amount": f"{tax_exclusive:.2f}",
            "tax_inclusive_amount": f"{tax_inclusive:.2f}",
            "allowance_total_amount": f"{total_discount:.2f}",
            "charge_total_amount": "0.00",
            "payable_amount": f"{payable:.2f}",
        }
    
    def _build_taxes(self, parsed: dict) -> list:
        """Construir tax_totals - agrupa por tax_id Y porcentaje"""
        lines = parsed.get("lines", [])
        subtotal = float(parsed.get("subtotal", 0))
        
        # Agrupar impuestos por (tax_id, percent)
        # tax_id: 1=IVA, 4=INC
        tax_groups = {}
        for line in lines:
            tax_id = int(line.get("tax_id", 1))
            percent = float(line.get("tax_percent", 0))
            key = f"{tax_id}_{percent:.2f}"
            
            if key not in tax_groups:
                tax_groups[key] = {
                    "tax_id": tax_id,
                    "tax_amount": 0,
                    "taxable_amount": 0,
                    "percent": percent
                }
            tax_groups[key]["tax_amount"] += float(line.get("tax_amount", 0))
            tax_groups[key]["taxable_amount"] += float(line.get("total", 0))
        
        # Si no hay impuestos, crear uno con IVA 0%
        if not tax_groups:
            return [{
                "tax_id": 1,
                "tax_amount": "0.00",
                "percent": "0.00",
                "taxable_amount": f"{subtotal:.2f}",
            }]
        
        # Construir lista de tax_totals
        result = []
        for g in tax_groups.values():
            result.append({
                "tax_id": g["tax_id"],
                "tax_amount": f"{g['tax_amount']:.2f}",
                "percent": f"{g['percent']:.2f}",
                "taxable_amount": f"{g['taxable_amount']:.2f}",
            })
        
        return result
    
    def _build_lines(self, lines: list) -> list:
        """Construir líneas de factura con tax_id correcto (IVA=1, INC=4)"""
        result = []
        for i, line in enumerate(lines):
            quantity = float(line.get("quantity", 1))
            total = float(line.get("total", 0))
            tax_id = int(line.get("tax_id", 1))  # 1=IVA, 4=INC
            tax_percent = float(line.get("tax_percent", 0))
            tax_amount = float(line.get("tax_amount", 0))
            unit_price = float(line.get("unit_price", total / quantity if quantity > 0 else total))
            
            result.append({
                "unit_measure_id": 70,
                "invoiced_quantity": f"{quantity:.2f}",
                "line_extension_amount": f"{total:.2f}",
                "free_of_charge_indicator": False,
                "tax_totals": [{
                    "tax_id": tax_id,
                    "tax_amount": f"{tax_amount:.2f}",
                    "percent": f"{tax_percent:.2f}",
                    "taxable_amount": f"{total:.2f}",
                }],
                "description": line.get("description", line.get("name", "Producto")),
                "code": str(line.get("code", str(i + 1))),
                "type_item_identification_id": 4,
                "price_amount": f"{unit_price:.2f}",
                "base_quantity": f"{quantity:.2f}",
            })
        return result
    
    def _build_ds_lines(self, lines: list) -> list:
        """Construir líneas para documento soporte con allowance_charges (OBLIGATORIO)"""
        result = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        for i, line in enumerate(lines):
            quantity = float(line.get("quantity", 1))
            total = float(line.get("total", 0))
            tax_id = int(line.get("tax_id", 1))  # 1=IVA, 4=INC
            tax_percent = float(line.get("tax_percent", 0))
            tax_amount = float(line.get("tax_amount", 0))
            unit_price = float(line.get("unit_price", total / quantity if quantity > 0 else total))
            
            result.append({
                "unit_measure_id": 70,
                "invoiced_quantity": f"{quantity:.2f}",
                "line_extension_amount": f"{total:.2f}",
                "free_of_charge_indicator": False,
                # Descuentos a nivel línea (OBLIGATORIO aunque sea 0)
                "allowance_charges": [{
                    "charge_indicator": False,
                    "allowance_charge_reason": "DESCUENTO GENERAL",
                    "amount": "0.00",
                    "base_amount": f"{total:.2f}",
                }],
                "tax_totals": [{
                    "tax_id": tax_id,
                    "tax_amount": f"{tax_amount:.2f}",
                    "taxable_amount": f"{total:.2f}",
                    "percent": f"{tax_percent:.2f}",
                }],
                "description": line.get("description", line.get("name", "Producto")),
                "notes": "",
                "code": str(line.get("code", str(i + 1))),
                "type_item_identification_id": 4,
                "price_amount": f"{unit_price:.2f}",
                "base_quantity": f"{quantity:.2f}",
                "type_generation_transmition_id": 1,
                "start_date": today,
            })
        return result
    
    def _process_response(self, document: Document, result: dict):
        """Procesar respuesta de la API"""
        session = get_session()
        doc = session.query(Document).get(document.id)
        
        doc.api_response = result
        
        if result.get("success"):
            # Buscar respuesta de la DIAN
            response_dian = result.get("ResponseDian", {}).get("Envelope", {}).get("Body", {})
            
            # Puede ser SendBillSyncResponse o SendTestSetAsyncResponse
            sync_result = response_dian.get("SendBillSyncResponse", {}).get("SendBillSyncResult", {})
            async_result = response_dian.get("SendTestSetAsyncResponse", {}).get("SendTestSetAsyncResult", {})
            dian_result = sync_result or async_result
            
            # Verificar si la DIAN procesó correctamente
            is_valid = dian_result.get("IsValid", "false")
            status_code = dian_result.get("StatusCode", "")
            status_description = dian_result.get("StatusDescription", "")
            error_messages = dian_result.get("ErrorMessage", {})
            
            # Extraer mensajes de error si existen
            error_list = []
            if isinstance(error_messages, dict):
                error_list = error_messages.get("string", [])
                if isinstance(error_list, str):
                    error_list = [error_list]
            elif isinstance(error_messages, list):
                error_list = error_messages
            
            # Buscar CUFE/CUDS (cuds para documento soporte, cufe para facturas)
            cufe = result.get("cuds") or result.get("cufe") or result.get("uuid") or result.get("cude") or dian_result.get("XmlDocumentKey")
            
            # Detectar rechazos - buscar "Rechazo" en cualquier parte del mensaje
            rejections = [e for e in error_list if "Rechazo" in e or "rechazo" in e.lower()]
            notifications = [e for e in error_list if "Notificación" in e and "Rechazo" not in e]
            
            # Determinar estado basado en la respuesta de la DIAN
            if rejections:
                # Documento RECHAZADO por la DIAN
                doc.status = "rejected"
                doc.error_message = "; ".join(rejections[:3])
                doc.cufe = None  # No guardar CUFE/CUDS si fue rechazado
            elif is_valid == "true" and status_code == "00":
                # Procesado correctamente
                doc.status = "sent"
                doc.sent_at = datetime.now()
                if cufe:
                    doc.cufe = cufe
                doc.error_message = "; ".join(notifications[:2]) if notifications else None
            elif cufe and not error_list:
                # Tiene CUFE/CUDS y no hay errores
                doc.status = "sent"
                doc.sent_at = datetime.now()
                doc.cufe = cufe
                doc.error_message = None
            elif error_list:
                # Hay errores pero no son rechazos explícitos - verificar si son solo notificaciones
                if all("Notificación" in e for e in error_list):
                    doc.status = "sent"
                    doc.sent_at = datetime.now()
                    if cufe:
                        doc.cufe = cufe
                    doc.error_message = "; ".join(notifications[:2])
                else:
                    # Errores no clasificados - marcar como error
                    doc.status = "error"
                    doc.error_message = "; ".join(error_list[:3])
            else:
                # Sin información clara, marcar como procesando
                doc.status = "processing"
        else:
            doc.status = "error"
            doc.error_message = result.get("message", "Error desconocido")
        
        session.commit()
        session.close()
    
    def download_pdf(self, document: Document) -> dict:
        """Descargar PDF del documento"""
        api_response = document.api_response or {}
        pdf_filename = api_response.get("urlinvoicepdf")
        
        if not pdf_filename:
            return {"success": False, "message": "No hay PDF disponible"}
        
        url = f"{self.base_url}/download/{self.settings.company_nit}/{pdf_filename}"
        return self._get(url)
    
    def download_attached(self, document: Document) -> dict:
        """Descargar AttachedDocument"""
        api_response = document.api_response or {}
        xml_filename = api_response.get("urlinvoiceattached")
        
        if not xml_filename:
            return {"success": False, "message": "No hay XML disponible"}
        
        url = f"{self.base_url}/download/{self.settings.company_nit}/{xml_filename}"
        return self._get(url)

    def send_email(self, document: Document) -> dict:
        """Enviar documento por correo electrónico con PDF y XML en ZIP"""
        import smtplib
        import zipfile
        import tempfile
        import os
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.base import MIMEBase
        from email import encoders
        
        if not document.customer_email:
            return {"success": False, "message": "El cliente no tiene correo electrónico"}
        
        # Verificar configuración de correo
        if not self.settings.mail_host or not self.settings.mail_username:
            return {"success": False, "message": "Configuración de correo incompleta. Configure SMTP en Ajustes."}
        
        try:
            # Descargar PDF
            pdf_result = self.download_pdf(document)
            pdf_content = pdf_result.get("content") if pdf_result.get("success") else None
            api_response = document.api_response or {}
            pdf_filename = api_response.get("urlinvoicepdf", f"{document.full_number}.pdf")
            
            # Descargar AttachedDocument (XML)
            xml_result = self.download_attached(document)
            xml_content = xml_result.get("content") if xml_result.get("success") else None
            xml_filename = api_response.get("urlinvoiceattached", f"{document.full_number}.xml")
            
            # Si no hay XML de ApiDian, usar el original
            if not xml_content and document.xml_content:
                xml_content = document.xml_content.encode('utf-8') if isinstance(document.xml_content, str) else document.xml_content
                xml_filename = document.xml_filename or f"{document.full_number}.xml"
            
            if not pdf_content and not xml_content:
                return {"success": False, "message": "No hay archivos disponibles para enviar"}
            
            # Crear ZIP temporal
            zip_filename = f"{document.prefix}{document.number}.zip"
            temp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(temp_dir, zip_filename)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if pdf_content:
                    zipf.writestr(pdf_filename, pdf_content)
                if xml_content:
                    zipf.writestr(xml_filename, xml_content)
            
            # Leer contenido del ZIP
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            # Limpiar archivo temporal
            os.remove(zip_path)
            os.rmdir(temp_dir)
            
            # Crear mensaje de correo
            msg = MIMEMultipart()
            msg['From'] = self.settings.mail_username
            msg['To'] = document.customer_email
            msg['Subject'] = f"Documento Electrónico {document.full_number} - {self.settings.company_name}"
            
            # Cuerpo del mensaje
            type_names = {"invoice": "Factura", "credit_note": "Nota Crédito", "debit_note": "Nota Débito"}
            type_name = type_names.get(document.type, "Documento")
            
            body = f"""
Estimado(a) {document.customer_name},

Adjunto encontrará su {type_name} Electrónica número {document.full_number}.

El archivo ZIP contiene:
- PDF del documento
- XML (AttachedDocument) para sus registros

Total: $ {document.total:,.0f}

Cordialmente,
{self.settings.company_name}
NIT: {self.settings.company_nit}
            """.strip()
            
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Adjuntar ZIP
            attachment = MIMEBase('application', 'zip')
            attachment.set_payload(zip_content)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename="{zip_filename}"')
            msg.attach(attachment)
            
            # Enviar correo
            port = int(self.settings.mail_port or 587)
            encryption = self.settings.mail_encryption or 'tls'
            
            if encryption == 'ssl':
                server = smtplib.SMTP_SSL(self.settings.mail_host, port)
            else:
                server = smtplib.SMTP(self.settings.mail_host, port)
                if encryption == 'tls':
                    server.starttls()
            
            server.login(self.settings.mail_username, self.settings.mail_password)
            server.send_message(msg)
            server.quit()
            
            return {"success": True, "message": f"Correo enviado exitosamente a {document.customer_email}"}
            
        except Exception as e:
            return {"success": False, "message": f"Error enviando correo: {str(e)}"}

    def get_numbering_range(self) -> dict:
        """Consultar resoluciones desde la DIAN"""
        url = f"{self.base_url}/numbering-range"
        data = {
            "IDSoftware": self.settings.software_id,
        }
        return self._post(url, data)

    def upload_certificate(self, certificate_base64: str, password: str) -> dict:
        """Subir certificado digital a ApiDian"""
        url = f"{self.base_url}/config/certificate"
        data = {
            "certificate": certificate_base64,
            "password": password,
        }
        result = self._put(url, data)
        
        # Si hay error, intentar extraer el mensaje de la respuesta
        if not result.get("success"):
            # Buscar mensaje de error en diferentes lugares de la respuesta
            error_msg = result.get("message", "")
            if not error_msg:
                error_msg = result.get("errors", {})
                if isinstance(error_msg, dict):
                    # Concatenar todos los errores
                    msgs = []
                    for key, val in error_msg.items():
                        if isinstance(val, list):
                            msgs.extend(val)
                        else:
                            msgs.append(str(val))
                    error_msg = ", ".join(msgs) if msgs else "Error desconocido"
            result["message"] = error_msg
        
        return result

    def configure_environment(self, type_environment_id: int) -> dict:
        """Cambiar ambiente de facturación (1=Producción, 2=Habilitación)"""
        url = f"{self.base_url}/config/environment"
        data = {
            "type_environment_id": type_environment_id,
        }
        result = self._put(url, data)
        
        if result.get("success"):
            # Actualizar configuración local
            session = get_session()
            settings = session.query(Settings).first()
            if settings:
                settings.type_environment_id = type_environment_id
                # Limpiar test_set_id si pasamos a producción
                if type_environment_id == 1:
                    settings.test_set_id = None
                session.commit()
            session.close()
            
            env_name = "Producción" if type_environment_id == 1 else "Habilitación"
            result["message"] = f"Ambiente cambiado a {env_name} exitosamente"
        
        return result
