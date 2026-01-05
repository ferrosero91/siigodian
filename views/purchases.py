"""Vista de Compras - Documento Soporte Electrónico"""
import flet as ft
from datetime import datetime
from database import (
    get_session, Document, Customer, Product, Resolution, Settings,
    TypeDocumentIdentification, TypeOrganization, TypeRegime, TypeLiability,
    Department, Municipality
)
from services import ApiDianService
from views.theme import COLORS, button, text_field, dropdown, section_title, divider, snackbar


class PurchasesView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.documents = []
        self.search_text = ""
        self.current_page = 1
        self.per_page = 15
        self.current_tab = 0  # 0=Pendientes, 1=Enviados
        self.catalogs = {}
        self._load_catalogs()

    def _load_catalogs(self):
        """Cargar catálogos DIAN"""
        session = get_session()
        self.catalogs["type_documents"] = {t.id: t.name for t in session.query(TypeDocumentIdentification).all()}
        self.catalogs["type_organizations"] = {t.id: t.name for t in session.query(TypeOrganization).all()}
        self.catalogs["type_regimes"] = {t.id: t.name for t in session.query(TypeRegime).all()}
        self.catalogs["type_liabilities"] = {t.id: t.name for t in session.query(TypeLiability).all()}
        self.catalogs["departments"] = {d.id: d.name for d in session.query(Department).order_by(Department.name).all()}
        self.catalogs["municipalities"] = session.query(Municipality).all()
        session.close()

    def _load_documents(self):
        session = get_session()
        query = session.query(Document).filter(Document.type.in_(["support_document", "sd_adjustment_note"]))
        
        if self.current_tab == 0:
            query = query.filter(Document.status.in_(["pending", "error"]))
        else:
            query = query.filter(Document.status.in_(["sent", "rejected"]))
        
        if self.search_text:
            search = f"%{self.search_text}%"
            query = query.filter(
                (Document.full_number.like(search)) |
                (Document.customer_name.like(search)) |
                (Document.customer_nit.like(search))
            )
        
        self.total_documents = query.count()
        self.documents = query.order_by(Document.created_at.desc()).offset(
            (self.current_page - 1) * self.per_page).limit(self.per_page).all()
        session.close()

    def build(self) -> ft.Container:
        self._load_documents()
        
        # Tabs
        self.tabs = ft.Tabs(
            selected_index=self.current_tab,
            tabs=[
                ft.Tab(text="Pendientes", icon=ft.Icons.PENDING_ACTIONS),
                ft.Tab(text="Enviados", icon=ft.Icons.CHECK_CIRCLE),
            ],
            on_change=self._on_tab_change,
            indicator_color=COLORS["primary"],
            label_color=COLORS["text_primary"],
            unselected_label_color=COLORS["text_secondary"],
        )
        
        # Buscador
        self.search_field = ft.TextField(
            hint_text="Buscar por número, proveedor o NIT...",
            prefix_icon=ft.Icons.SEARCH,
            width=300,
            height=40,
            text_size=13,
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            on_change=self._on_search,
        )
        
        # Header
        header = ft.Row([
            ft.Icon(ft.Icons.SHOPPING_CART, color=COLORS["primary"], size=28),
            ft.Text("Documento Soporte Electrónico", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
            ft.Container(expand=True),
            self.search_field,
            button("Nuevo DS", self._show_new_document_form, color="success", icon=ft.Icons.ADD),
            button("Actualizar", lambda e: self._refresh(), color="info", icon=ft.Icons.REFRESH),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        # Info box
        info_box = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, color=COLORS["info"], size=20),
                ft.Text(
                    "El Documento Soporte es obligatorio para compras a proveedores no obligados a facturar (personas naturales sin NIT, régimen simplificado).",
                    color=COLORS["text_secondary"],
                    size=12,
                ),
            ], spacing=10),
            bgcolor=COLORS["bg_secondary"],
            padding=12,
            border_radius=8,
        )
        
        # Tabla
        self.table_container = ft.Container(content=self._build_table(), expand=True)
        
        # Paginación
        self.pagination = self._build_pagination()
        
        return ft.Container(
            content=ft.Column([
                header,
                info_box,
                self.tabs,
                divider(),
                self.table_container,
                self.pagination,
            ], expand=True, spacing=10),
            expand=True, padding=24, bgcolor=COLORS["bg_primary"],
        )

    def _build_table(self) -> ft.DataTable:
        rows = []
        for d in self.documents:
            status_colors = {
                "pending": COLORS["warning"],
                "sent": COLORS["success"],
                "error": COLORS["danger"],
                "rejected": COLORS["danger"],
            }
            status_color = status_colors.get(d.status, COLORS["text_secondary"])
            
            # Determinar tipo de documento
            type_label = "DS" if d.type == "support_document" else "NA-DS"
            type_color = COLORS["primary"] if d.type == "support_document" else COLORS["warning"]
            
            rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Container(
                        content=ft.Text(type_label, color="white", size=10, weight=ft.FontWeight.BOLD),
                        bgcolor=type_color,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4,
                    )),
                    ft.DataCell(ft.Text(d.full_number or "", color=COLORS["primary"], size=13, weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Text(d.issue_date.strftime("%Y-%m-%d") if d.issue_date else "", 
                                       color=COLORS["text_secondary"], size=12)),
                    ft.DataCell(ft.Container(
                        content=ft.Column([
                            ft.Text(d.customer_name or "", color=COLORS["text_primary"], size=13),
                            ft.Text(d.customer_nit or "", color=COLORS["text_secondary"], size=11),
                        ], spacing=2),
                        width=200,
                    )),
                    ft.DataCell(ft.Text(f"$ {d.total:,.0f}", color=COLORS["text_primary"], size=13)),
                    ft.DataCell(ft.Container(
                        content=ft.Text(d.status_label, color="white", size=11),
                        bgcolor=status_color,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=4,
                    )),
                    ft.DataCell(ft.Row([
                        ft.IconButton(ft.Icons.SEND, icon_color=COLORS["success"], icon_size=18,
                                     tooltip="Enviar a DIAN", 
                                     on_click=lambda e, did=d.id: self._send_document(did),
                                     visible=d.status in ["pending", "error"]),
                        ft.IconButton(ft.Icons.CANCEL, icon_color=COLORS["warning"], icon_size=18,
                                     tooltip="Nota de Ajuste (Anular)", 
                                     on_click=lambda e, did=d.id: self._show_adjustment_note_form(did),
                                     visible=d.status == "sent" and d.cufe and d.type == "support_document"),
                        ft.IconButton(ft.Icons.VISIBILITY, icon_color=COLORS["info"], icon_size=18,
                                     tooltip="Ver detalle", on_click=lambda e, did=d.id: self._view_document(did)),
                        ft.IconButton(ft.Icons.DELETE, icon_color=COLORS["danger"], icon_size=18,
                                     tooltip="Eliminar", on_click=lambda e, did=d.id: self._delete_document(did),
                                     visible=d.status == "pending"),
                    ], spacing=0)),
                ],
            ))
        
        if not rows:
            return ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.INBOX, color=COLORS["text_secondary"], size=48),
                    ft.Text("No hay documentos", color=COLORS["text_secondary"], size=14),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.alignment.center,
                expand=True,
                padding=40,
            )
        
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Tipo", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Número", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Fecha", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Proveedor", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Total", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Estado", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Acciones", color=COLORS["text_secondary"], size=12)),
            ],
            rows=rows,
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            heading_row_color=COLORS["bg_secondary"],
            data_row_max_height=60,
        )

    def _build_pagination(self) -> ft.Row:
        total_pages = max(1, (self.total_documents + self.per_page - 1) // self.per_page)
        return ft.Row([
            ft.Text(f"Total: {self.total_documents}", color=COLORS["text_secondary"], size=12),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=self._prev_page,
                         disabled=self.current_page <= 1, icon_color=COLORS["text_secondary"]),
            ft.Text(f"Página {self.current_page} de {total_pages}", color=COLORS["text_primary"], size=13),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=self._next_page,
                         disabled=self.current_page >= total_pages, icon_color=COLORS["text_secondary"]),
        ], alignment=ft.MainAxisAlignment.CENTER)

    def _on_tab_change(self, e):
        self.current_tab = e.control.selected_index
        self.current_page = 1
        self._refresh()

    def _on_search(self, e):
        self.search_text = e.control.value
        self.current_page = 1
        self._refresh()

    def _prev_page(self, e):
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh()

    def _next_page(self, e):
        total_pages = max(1, (self.total_documents + self.per_page - 1) // self.per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self._refresh()

    def _refresh(self):
        self._load_documents()
        self.table_container.content = self._build_table()
        self.pagination.controls = self._build_pagination().controls
        self.page.update()

    def _show_new_document_form(self, e):
        """Mostrar formulario para nuevo documento soporte"""
        session = get_session()
        suppliers = session.query(Customer).filter(Customer.type == "supplier", Customer.is_active == True).all()
        products = session.query(Product).filter(Product.is_active == True).all()
        
        # Obtener resolución de DS
        resolution = session.query(Resolution).filter(
            Resolution.type_document_id == 11,
            Resolution.is_active == True
        ).first()
        session.close()
        
        if not resolution:
            snackbar(self.page, "Configure una resolución para Documento Soporte (tipo 11) primero", "warning")
            return
        
        # Estado del formulario
        self.form_lines = []
        self.selected_supplier = None
        
        # Indicador de carga para consulta DIAN
        loading_indicator = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        
        # Campos del proveedor
        fields = {}
        fields["supplier"] = dropdown("Proveedor Existente (opcional)", "",
            [ft.dropdown.Option("", "-- Nuevo proveedor --")] + 
            [ft.dropdown.Option(str(s.id), f"{s.identification_number} - {s.name}") for s in suppliers],
            width=450)
        fields["supplier"].on_change = lambda e: self._on_supplier_change(e, fields)
        
        # Datos básicos del proveedor
        fields["supplier_nit"] = text_field("NIT/CC *", "", width=180)
        fields["supplier_name"] = text_field("Nombre/Razón Social *", "", width=350)
        fields["supplier_phone"] = text_field("Teléfono", "", width=150)
        fields["supplier_email"] = text_field("Email", "", width=250)
        fields["supplier_address"] = text_field("Dirección", "", width=350)
        
        # Datos DIAN del proveedor
        fields["type_document_id"] = dropdown("Tipo Documento", "3",
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_documents"].items()], width=220)
        fields["type_organization_id"] = dropdown("Tipo Organización", "2",
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_organizations"].items()], width=220)
        fields["type_regime_id"] = dropdown("Régimen", "2",
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_regimes"].items()], width=200)
        fields["type_liability_id"] = dropdown("Responsabilidad", "117",
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_liabilities"].items()], width=220)
        fields["department_id"] = dropdown("Departamento", "22",
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["departments"].items()], width=200)
        fields["department_id"].on_change = lambda e: self._on_department_change(e, fields)
        
        def search_dian_supplier(e):
            """Consultar proveedor en la DIAN"""
            doc_type = fields["type_document_id"].value
            doc_number = fields["supplier_nit"].value
            
            if not doc_type or not doc_number:
                snackbar(self.page, "Ingrese tipo y número de documento", "warning")
                return
            
            loading_indicator.visible = True
            self.page.update()
            
            try:
                result = ApiDianService().get_acquirer(int(doc_type), doc_number)
                
                if result.get("success"):
                    name = result.get("name", "")
                    email = result.get("email", "")
                    
                    if name:
                        fields["supplier_name"].value = name
                    if email:
                        fields["supplier_email"].value = email
                    
                    self.page.update()
                    snackbar(self.page, "Datos encontrados en DIAN", "success")
                else:
                    snackbar(self.page, result.get("message", "No se encontró información"), "warning")
            except Exception as ex:
                snackbar(self.page, f"Error: {str(ex)}", "danger")
            finally:
                loading_indicator.visible = False
                self.page.update()
        
        # Botón de búsqueda DIAN
        search_dian_btn = ft.IconButton(
            ft.Icons.SEARCH,
            icon_color=COLORS["primary"],
            tooltip="Consultar en DIAN",
            on_click=search_dian_supplier,
        )
        
        # Municipios filtrados
        dept_id = 22  # Nariño por defecto
        muni_options = [ft.dropdown.Option(str(m.id), m.name) for m in self.catalogs["municipalities"] if m.department_id == dept_id]
        fields["municipality_id"] = dropdown("Municipio", "520",
            muni_options if muni_options else [ft.dropdown.Option("520", "Pasto")], width=200)
        
        # Campos de producto
        fields["product"] = dropdown("Agregar Producto", "",
            [ft.dropdown.Option(str(p.id), f"{p.code} - {p.name}") for p in products],
            width=300)
        fields["quantity"] = text_field("Cantidad", "1", width=80)
        fields["unit_price"] = text_field("Precio (IVA inc.)", "", width=120)
        fields["tax_percent"] = dropdown("IVA %", "0",
            [ft.dropdown.Option("0", "0%"), ft.dropdown.Option("5", "5%"), ft.dropdown.Option("19", "19%")], width=80)
        
        # Contenedor de líneas
        self.lines_container = ft.Column([], spacing=8)
        
        # Totales
        self.subtotal_text = ft.Text("$ 0", color=COLORS["text_primary"], size=14)
        self.tax_text = ft.Text("$ 0", color=COLORS["text_primary"], size=14)
        self.total_text = ft.Text("$ 0", color=COLORS["text_primary"], size=18, weight=ft.FontWeight.BOLD)
        
        self.form_fields = fields
        
        def add_line(e):
            if not fields["product"].value:
                snackbar(self.page, "Seleccione un producto", "warning")
                return
            
            session = get_session()
            product = session.query(Product).get(int(fields["product"].value))
            session.close()
            
            if product:
                qty = float(fields["quantity"].value or 1)
                price = float(fields["unit_price"].value or product.unit_price)
                tax_pct = float(fields["tax_percent"].value or product.tax_percent or 0)
                
                # El precio ingresado se asume que INCLUYE IVA (como en una compra real)
                # Calcular precio sin IVA para mostrar correctamente
                if tax_pct > 0:
                    price_without_tax = price / (1 + (tax_pct / 100))
                else:
                    price_without_tax = price
                
                subtotal = qty * price_without_tax  # Base imponible
                tax = subtotal * (tax_pct / 100)    # Impuesto
                total_line = subtotal + tax         # Total con IVA
                
                line = {
                    "product_id": product.id,
                    "code": product.code,
                    "name": product.name,
                    "description": product.name,
                    "quantity": qty,
                    "unit_price": price,  # Precio CON IVA (como se ingresó)
                    "tax_percent": tax_pct,
                    "tax_id": 1,  # IVA
                    "tax_amount": tax,
                    "total": subtotal,  # Base imponible (line_extension_amount)
                }
                self.form_lines.append(line)
                self._update_lines_display()
                
                # Limpiar campos
                fields["product"].value = ""
                fields["quantity"].value = "1"
                fields["unit_price"].value = ""
                self.page.update()

        def save_document(e):
            if not fields["supplier_nit"].value:
                snackbar(self.page, "Ingrese el NIT/CC del proveedor", "warning")
                return
            if not fields["supplier_name"].value:
                snackbar(self.page, "Ingrese el nombre del proveedor", "warning")
                return
            if not self.form_lines:
                snackbar(self.page, "Agregue al menos un producto", "warning")
                return
            
            # Calcular totales
            subtotal = sum(l["total"] for l in self.form_lines)
            total_tax = sum(l["tax_amount"] for l in self.form_lines)
            total = subtotal + total_tax
            
            session = get_session()
            resolution = session.query(Resolution).filter(
                Resolution.type_document_id == 11,
                Resolution.is_active == True
            ).first()
            
            if not resolution:
                session.close()
                snackbar(self.page, "No hay resolución de DS configurada", "danger")
                return
            
            next_number = resolution.current_number + 1
            if next_number > resolution.to_number:
                session.close()
                snackbar(self.page, "Se agotó el rango de numeración", "danger")
                return
            
            prefix_value = resolution.prefix
            full_number_value = f"{prefix_value}{next_number}"
            
            # Obtener código postal del municipio
            municipality_id = int(fields["municipality_id"].value or 520)
            postal_zone_code = 110111  # Default Bogotá
            for m in self.catalogs["municipalities"]:
                if m.id == municipality_id:
                    # Usar el código del municipio como código postal
                    postal_zone_code = int(m.code) if m.code and m.code.isdigit() else 110111
                    break
            
            # Datos del proveedor para el payload
            supplier_data = {
                "identification_number": fields["supplier_nit"].value,
                "name": fields["supplier_name"].value,
                "phone": fields["supplier_phone"].value or "0000000",
                "email": fields["supplier_email"].value or "proveedor@email.com",
                "address": fields["supplier_address"].value or "DIRECCION",
                "type_document_identification_id": int(fields["type_document_id"].value or 3),
                "type_organization_id": int(fields["type_organization_id"].value or 2),
                "type_regime_id": int(fields["type_regime_id"].value or 2),
                "type_liability_id": int(fields["type_liability_id"].value or 117),
                "municipality_id": municipality_id,
                "postal_zone_code": postal_zone_code,
                "merchant_registration": "0000000-00",
            }
            
            # Crear documento
            doc = Document(
                type="support_document",
                type_document_id=11,
                prefix=prefix_value,
                number=str(next_number),
                full_number=full_number_value,
                issue_date=datetime.now(),
                customer_nit=fields["supplier_nit"].value,
                customer_name=fields["supplier_name"].value,
                customer_email=fields["supplier_email"].value or "",
                subtotal=subtotal,
                total_tax=total_tax,
                total=total,
                status="pending",
                parsed_data={
                    "lines": self.form_lines,
                    "customer": supplier_data,
                    "subtotal": subtotal,
                    "total_tax": total_tax,
                    "total": total,
                },
            )
            session.add(doc)
            resolution.current_number = next_number
            session.commit()
            session.close()
            
            dlg.open = False
            self.page.update()
            self._refresh()
            snackbar(self.page, f"Documento {full_number_value} creado", "success")
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()

        # Construir diálogo
        dlg = ft.AlertDialog(
            title=ft.Text("Nuevo Documento Soporte", size=18, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
            content=ft.Container(
                content=ft.Column([
                    # Sección Proveedor
                    section_title("Proveedor", "Datos del vendedor (no obligado a facturar)"),
                    fields["supplier"],
                    ft.Row([fields["supplier_nit"], search_dian_btn, loading_indicator, fields["supplier_name"]], spacing=8),
                    ft.Row([fields["supplier_phone"], fields["supplier_email"]], spacing=12),
                    fields["supplier_address"],
                    ft.ExpansionTile(
                        title=ft.Text("Datos DIAN del proveedor", size=13, color=COLORS["text_secondary"]),
                        initially_expanded=False,
                        controls=[
                            ft.Container(
                                content=ft.Column([
                                    ft.Row([fields["type_document_id"], fields["type_organization_id"]], spacing=12),
                                    ft.Row([fields["type_regime_id"], fields["type_liability_id"]], spacing=12),
                                    ft.Row([fields["department_id"], fields["municipality_id"]], spacing=12),
                                ], spacing=8),
                                padding=10,
                            ),
                        ],
                    ),
                    divider(),
                    # Sección Productos
                    section_title("Productos/Servicios", "Agregue los items de la compra"),
                    ft.Row([
                        fields["product"],
                        fields["quantity"],
                        fields["unit_price"],
                        fields["tax_percent"],
                        ft.IconButton(ft.Icons.ADD_CIRCLE, icon_color=COLORS["success"], 
                                     tooltip="Agregar", on_click=add_line),
                    ], spacing=8),
                    ft.Container(
                        content=self.lines_container,
                        bgcolor=COLORS["bg_secondary"],
                        padding=10,
                        border_radius=8,
                        height=150,
                    ),
                    divider(),
                    # Totales
                    ft.Row([
                        ft.Container(expand=True),
                        ft.Column([
                            ft.Row([ft.Text("Subtotal:", color=COLORS["text_secondary"], width=80), self.subtotal_text]),
                            ft.Row([ft.Text("IVA:", color=COLORS["text_secondary"], width=80), self.tax_text]),
                            ft.Row([ft.Text("TOTAL:", color=COLORS["text_primary"], weight=ft.FontWeight.BOLD, width=80), self.total_text]),
                        ], spacing=4),
                    ]),
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
                width=700, height=600,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Crear Documento", on_click=save_document, bgcolor=COLORS["success"], color="white"),
            ],
            bgcolor=COLORS["bg_card"],
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _on_supplier_change(self, e, fields):
        """Cargar datos del proveedor seleccionado"""
        if e.control.value:
            session = get_session()
            supplier = session.query(Customer).get(int(e.control.value))
            session.close()
            
            if supplier:
                fields["supplier_nit"].value = supplier.identification_number or ""
                fields["supplier_name"].value = supplier.name or ""
                fields["supplier_phone"].value = supplier.phone or ""
                fields["supplier_email"].value = supplier.email or ""
                fields["supplier_address"].value = supplier.address or ""
                fields["type_document_id"].value = str(supplier.type_document_identification_id or 3)
                fields["type_organization_id"].value = str(supplier.type_organization_id or 2)
                fields["type_regime_id"].value = str(supplier.type_regime_id or 2)
                fields["type_liability_id"].value = str(supplier.type_liability_id or 117)
                if supplier.department_id:
                    fields["department_id"].value = str(supplier.department_id)
                    # Actualizar municipios
                    muni_options = [ft.dropdown.Option(str(m.id), m.name) 
                                   for m in self.catalogs["municipalities"] 
                                   if m.department_id == supplier.department_id]
                    fields["municipality_id"].options = muni_options
                if supplier.municipality_id:
                    fields["municipality_id"].value = str(supplier.municipality_id)
                self.page.update()

    def _on_department_change(self, e, fields):
        """Actualizar municipios al cambiar departamento"""
        dept_id = int(e.control.value) if e.control.value else 0
        filtered = [(m.id, m.name) for m in self.catalogs["municipalities"] if m.department_id == dept_id]
        fields["municipality_id"].options = [ft.dropdown.Option(str(k), name) for k, name in filtered]
        if filtered:
            fields["municipality_id"].value = str(filtered[0][0])
        self.page.update()

    def _update_lines_display(self):
        """Actualizar visualización de líneas"""
        self.lines_container.controls.clear()
        
        for i, line in enumerate(self.form_lines):
            self.lines_container.controls.append(
                ft.Row([
                    ft.Text(f"{line['quantity']:.0f}x", color=COLORS["text_secondary"], size=12, width=40),
                    ft.Text(line["name"], color=COLORS["text_primary"], size=12, expand=True),
                    ft.Text(f"${line['unit_price']:,.0f}", color=COLORS["text_secondary"], size=12, width=80),
                    ft.Text(f"{line['tax_percent']:.0f}%", color=COLORS["info"], size=11, width=40),
                    ft.Text(f"${line['total']:,.0f}", color=COLORS["text_primary"], size=12, width=90),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=COLORS["danger"], icon_size=16,
                                 on_click=lambda e, idx=i: self._remove_line(idx)),
                ], spacing=8)
            )
        
        # Actualizar totales
        subtotal = sum(l["total"] for l in self.form_lines)
        total_tax = sum(l["tax_amount"] for l in self.form_lines)
        total = subtotal + total_tax
        
        self.subtotal_text.value = f"$ {subtotal:,.0f}"
        self.tax_text.value = f"$ {total_tax:,.0f}"
        self.total_text.value = f"$ {total:,.0f}"
        
        self.page.update()

    def _remove_line(self, idx):
        """Eliminar línea del formulario"""
        if 0 <= idx < len(self.form_lines):
            self.form_lines.pop(idx)
            self._update_lines_display()

    def _send_document(self, doc_id):
        """Enviar documento soporte a la DIAN"""
        session = get_session()
        doc = session.query(Document).get(doc_id)
        
        if not doc:
            session.close()
            return
        
        # Extraer datos antes de cerrar sesión
        doc_type = doc.type
        doc_full_number = doc.full_number
        session.close()
        
        service = ApiDianService()
        
        if doc_type == "support_document":
            result = service.send_support_document(doc)
        else:
            result = service.send_sd_adjustment_note(doc)
        
        if result.get("success"):
            snackbar(self.page, f"Documento {doc_full_number} enviado exitosamente", "success")
        else:
            snackbar(self.page, f"Error: {result.get('message', 'Error desconocido')}", "danger")
        
        self._refresh()

    def _view_document(self, doc_id):
        """Ver detalle del documento"""
        session = get_session()
        doc = session.query(Document).get(doc_id)
        
        if not doc:
            session.close()
            return
        
        # Extraer datos antes de cerrar sesión
        full_number = doc.full_number
        customer_name = doc.customer_name
        customer_nit = doc.customer_nit
        issue_date = doc.issue_date
        status_label = doc.status_label
        type_label = doc.type_label
        subtotal = doc.subtotal
        total_tax = doc.total_tax
        total = doc.total
        cufe = doc.cufe
        error_message = doc.error_message
        parsed_data = doc.parsed_data
        reference_cufe = doc.reference_cufe
        
        # Obtener documento de referencia si existe
        ref_doc_number = None
        if doc.reference_document_id:
            ref_doc = session.query(Document).get(doc.reference_document_id)
            if ref_doc:
                ref_doc_number = ref_doc.full_number
        
        session.close()
        
        lines_text = ""
        if parsed_data and parsed_data.get("lines"):
            for l in parsed_data["lines"]:
                lines_text += f"• {l.get('quantity', 1):.0f}x {l.get('name', '')} - ${l.get('total', 0):,.0f}\n"
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        content_items = [
            ft.Row([ft.Text("Tipo:", color=COLORS["text_secondary"], width=100), 
                   ft.Text(type_label, color=COLORS["text_primary"])]),
            ft.Row([ft.Text("Proveedor:", color=COLORS["text_secondary"], width=100), 
                   ft.Text(customer_name, color=COLORS["text_primary"])]),
            ft.Row([ft.Text("NIT:", color=COLORS["text_secondary"], width=100), 
                   ft.Text(customer_nit, color=COLORS["text_primary"])]),
            ft.Row([ft.Text("Fecha:", color=COLORS["text_secondary"], width=100), 
                   ft.Text(issue_date.strftime("%Y-%m-%d %H:%M") if issue_date else "", color=COLORS["text_primary"])]),
            ft.Row([ft.Text("Estado:", color=COLORS["text_secondary"], width=100), 
                   ft.Text(status_label, color=COLORS["text_primary"])]),
        ]
        
        if ref_doc_number:
            content_items.append(
                ft.Row([ft.Text("Referencia:", color=COLORS["text_secondary"], width=100), 
                       ft.Text(ref_doc_number, color=COLORS["warning"])])
            )
        
        content_items.extend([
            divider(),
            ft.Text("Productos:", color=COLORS["text_secondary"]),
            ft.Text(lines_text, color=COLORS["text_primary"], size=12),
            divider(),
            ft.Row([ft.Text("Subtotal:", color=COLORS["text_secondary"], width=100), 
                   ft.Text(f"$ {subtotal:,.0f}", color=COLORS["text_primary"])]),
            ft.Row([ft.Text("IVA:", color=COLORS["text_secondary"], width=100), 
                   ft.Text(f"$ {total_tax:,.0f}", color=COLORS["text_primary"])]),
            ft.Row([ft.Text("TOTAL:", color=COLORS["text_primary"], weight=ft.FontWeight.BOLD, width=100), 
                   ft.Text(f"$ {total:,.0f}", color=COLORS["text_primary"], weight=ft.FontWeight.BOLD)]),
            ft.Container(height=8),
            ft.Text(f"CUDE: {cufe or 'Pendiente'}", color=COLORS["text_secondary"], size=11, selectable=True),
        ])
        
        if error_message:
            content_items.append(
                ft.Container(
                    content=ft.Text(f"Error: {error_message}", color=COLORS["danger"], size=11),
                    bgcolor=COLORS["bg_hover"],
                    padding=8,
                    border_radius=4,
                )
            )
        
        dlg = ft.AlertDialog(
            title=ft.Text(f"Documento {full_number}", size=18, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column(content_items, spacing=8),
                width=450,
            ),
            actions=[ft.TextButton("Cerrar", on_click=close_dlg)],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _delete_document(self, doc_id):
        """Eliminar documento pendiente"""
        def confirm_delete(e):
            session = get_session()
            doc = session.query(Document).get(doc_id)
            if doc and doc.status == "pending":
                session.delete(doc)
                session.commit()
            session.close()
            dlg.open = False
            self.page.update()
            self._refresh()
            snackbar(self.page, "Documento eliminado", "success")
        
        def cancel_delete(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar eliminación", color=COLORS["danger"]),
            content=ft.Text("¿Está seguro de eliminar este documento?", color=COLORS["text_primary"]),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_delete),
                ft.ElevatedButton("Eliminar", on_click=confirm_delete, bgcolor=COLORS["danger"], color="white"),
            ],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _show_adjustment_note_form(self, doc_id):
        """Mostrar formulario para crear nota de ajuste a documento soporte"""
        session = get_session()
        ref_doc = session.query(Document).get(doc_id)
        
        if not ref_doc or not ref_doc.cufe:
            session.close()
            snackbar(self.page, "El documento no tiene CUDE válido", "danger")
            return
        
        # Verificar resolución de nota de ajuste
        resolution = session.query(Resolution).filter(
            Resolution.type_document_id == 13,
            Resolution.is_active == True
        ).first()
        
        if not resolution:
            session.close()
            snackbar(self.page, "Configure una resolución para Nota de Ajuste a DS (tipo 13) primero", "warning")
            return
        
        # Extraer datos antes de cerrar sesión
        ref_full_number = ref_doc.full_number
        ref_customer_name = ref_doc.customer_name
        ref_customer_nit = ref_doc.customer_nit
        ref_customer_email = ref_doc.customer_email
        ref_cufe = ref_doc.cufe
        ref_subtotal = ref_doc.subtotal
        ref_total_tax = ref_doc.total_tax
        ref_total = ref_doc.total
        ref_parsed_data = ref_doc.parsed_data
        ref_id = ref_doc.id
        
        session.close()
        
        # Códigos de discrepancia para DS
        discrepancy_codes = [
            ("1", "Devolución parcial de los bienes y/o no aceptación parcial del servicio"),
            ("2", "Anulación"),
            ("3", "Rebaja o descuento parcial o total"),
            ("4", "Ajuste de precio"),
            ("5", "Otros"),
        ]
        
        discrepancy_dd = dropdown("Motivo de Ajuste", "2", 
            [ft.dropdown.Option(code, desc) for code, desc in discrepancy_codes], width=500)
        notes_tf = ft.TextField(
            label="Descripción/Notas",
            value="Anulación de documento soporte",
            multiline=True,
            min_lines=2,
            max_lines=3,
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            text_style=ft.TextStyle(color=COLORS["text_primary"]),
        )

        def create_adjustment_note(e):
            session = get_session()
            
            res = session.query(Resolution).filter(
                Resolution.type_document_id == 13,
                Resolution.is_active == True
            ).first()
            
            if not res:
                session.close()
                snackbar(self.page, "No hay resolución de Nota de Ajuste configurada", "danger")
                return
            
            next_number = res.current_number + 1
            if next_number > res.to_number:
                session.close()
                snackbar(self.page, "Se agotó el rango de numeración", "danger")
                return
            
            prefix_value = res.prefix
            full_number_value = f"{prefix_value}{next_number}"
            
            # Obtener datos del proveedor del documento original
            customer_data = ref_parsed_data.get("customer", {}) if ref_parsed_data else {}
            if not customer_data.get("identification_number"):
                customer_data = {
                    "identification_number": ref_customer_nit,
                    "name": ref_customer_name,
                    "email": ref_customer_email or "proveedor@email.com",
                    "phone": "0000000",
                    "address": "DIRECCION",
                    "type_document_identification_id": 3,
                    "type_organization_id": 2,
                    "type_regime_id": 2,
                    "type_liability_id": 117,
                    "municipality_id": 520,
                }
            
            # Crear nota de ajuste
            adj_note = Document(
                type="sd_adjustment_note",
                type_document_id=13,
                prefix=prefix_value,
                number=str(next_number),
                full_number=full_number_value,
                issue_date=datetime.now(),
                customer_nit=ref_customer_nit,
                customer_name=ref_customer_name,
                customer_email=ref_customer_email,
                subtotal=ref_subtotal,
                total_tax=ref_total_tax,
                total=ref_total,
                status="pending",
                reference_document_id=ref_id,
                reference_cufe=ref_cufe,
                parsed_data={
                    "lines": ref_parsed_data.get("lines", []) if ref_parsed_data else [],
                    "customer": customer_data,
                    "subtotal": ref_subtotal,
                    "total_tax": ref_total_tax,
                    "total": ref_total,
                    "discrepancy_code": discrepancy_dd.value,
                    "discrepancy_description": notes_tf.value,
                },
            )
            session.add(adj_note)
            res.current_number = next_number
            session.commit()
            
            # Enviar automáticamente a la DIAN
            service = ApiDianService()
            result = service.send_sd_adjustment_note(adj_note)
            
            session.close()
            
            dlg.open = False
            self.page.update()
            
            if result.get("success"):
                snackbar(self.page, f"Nota de Ajuste {full_number_value} enviada exitosamente", "success")
            else:
                snackbar(self.page, f"Nota creada pero error al enviar: {result.get('message', 'Error')}", "warning")
            
            self._refresh()
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.CANCEL, color=COLORS["warning"]),
                ft.Text("Nota de Ajuste a Documento Soporte", size=18, weight=ft.FontWeight.W_600),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Column([
                            ft.Text("Documento de Referencia:", color=COLORS["text_secondary"], size=12),
                            ft.Text(f"{ref_full_number} - {ref_customer_name}", 
                                   color=COLORS["text_primary"], weight=ft.FontWeight.W_600),
                            ft.Text(f"CUDE: {ref_cufe[:50]}...", color=COLORS["text_secondary"], size=11),
                            ft.Text(f"Total: $ {ref_total:,.0f}", color=COLORS["text_primary"]),
                        ], spacing=4),
                        bgcolor=COLORS["bg_secondary"],
                        padding=12,
                        border_radius=8,
                    ),
                    ft.Container(height=8),
                    discrepancy_dd,
                    notes_tf,
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.WARNING_AMBER, color=COLORS["warning"], size=16),
                            ft.Text(
                                "Esta acción creará y enviará una Nota de Ajuste a la DIAN para anular el documento soporte.",
                                color=COLORS["text_secondary"], size=12,
                            ),
                        ], spacing=8),
                        bgcolor=COLORS["bg_hover"],
                        padding=10,
                        border_radius=8,
                    ),
                ], spacing=12),
                width=550,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Crear y Enviar Nota de Ajuste", on_click=create_adjustment_note, 
                                 bgcolor=COLORS["warning"], color="white"),
            ],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
