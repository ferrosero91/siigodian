"""Vista de Clientes/Proveedores"""
import flet as ft
from database import (
    get_session, Customer,
    TypeDocumentIdentification, TypeOrganization, TypeRegime,
    TypeLiability, Department, Municipality
)
from views.theme import COLORS, button, text_field, dropdown, section_title, divider, snackbar


class CustomersView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.customers = []
        self.catalogs = {}
        self.search_text = ""
        self.current_page = 1
        self.per_page = 15
        self.show_type = "all"  # all, customer, supplier
        self._load_catalogs()

    def _load_catalogs(self):
        session = get_session()
        self.catalogs["type_documents"] = {t.id: t.name for t in session.query(TypeDocumentIdentification).all()}
        self.catalogs["type_organizations"] = {t.id: t.name for t in session.query(TypeOrganization).all()}
        self.catalogs["type_regimes"] = {t.id: t.name for t in session.query(TypeRegime).all()}
        self.catalogs["type_liabilities"] = {t.id: t.name for t in session.query(TypeLiability).all()}
        self.catalogs["departments"] = {d.id: d.name for d in session.query(Department).order_by(Department.name).all()}
        self.catalogs["municipalities"] = session.query(Municipality).all()
        session.close()

    def _load_customers(self):
        session = get_session()
        query = session.query(Customer)
        
        if self.show_type != "all":
            query = query.filter(Customer.type == self.show_type)
        
        if self.search_text:
            search = f"%{self.search_text}%"
            query = query.filter(
                (Customer.identification_number.like(search)) |
                (Customer.name.like(search)) |
                (Customer.email.like(search))
            )
        
        self.total_customers = query.count()
        self.customers = query.order_by(Customer.name).offset((self.current_page - 1) * self.per_page).limit(self.per_page).all()
        session.close()

    def build(self) -> ft.Container:
        self._load_customers()
        
        # Tabs para filtrar
        self.tabs = ft.Tabs(
            selected_index=0 if self.show_type == "all" else (1 if self.show_type == "customer" else 2),
            tabs=[
                ft.Tab(text="Todos", icon=ft.Icons.PEOPLE),
                ft.Tab(text="Clientes", icon=ft.Icons.PERSON),
                ft.Tab(text="Proveedores", icon=ft.Icons.STORE),
            ],
            on_change=self._on_tab_change,
            indicator_color=COLORS["primary"],
            label_color=COLORS["text_primary"],
            unselected_label_color=COLORS["text_secondary"],
        )
        
        # Buscador
        self.search_field = ft.TextField(
            hint_text="Buscar por NIT, nombre o email...",
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
            ft.Icon(ft.Icons.PEOPLE, color=COLORS["primary"], size=28),
            ft.Text("Clientes y Proveedores", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
            ft.Container(expand=True),
            self.search_field,
            button("Nuevo", self._show_form, color="success", icon=ft.Icons.ADD),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        # Tabla
        self.table_container = ft.Container(content=self._build_table(), expand=True)
        
        # Paginación
        self.pagination = self._build_pagination()
        
        return ft.Container(
            content=ft.Column([
                header,
                self.tabs,
                divider(),
                self.table_container,
                self.pagination,
            ], expand=True, spacing=10),
            expand=True, padding=24, bgcolor=COLORS["bg_primary"],
        )

    def _build_table(self) -> ft.DataTable:
        rows = []
        for c in self.customers:
            type_icon = ft.Icons.PERSON if c.type == "customer" else ft.Icons.STORE
            type_color = COLORS["info"] if c.type == "customer" else COLORS["warning"]
            
            rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Row([
                        ft.Icon(type_icon, color=type_color, size=18),
                        ft.Text(c.identification_number or "", color=COLORS["text_primary"], size=13),
                    ], spacing=8)),
                    ft.DataCell(ft.Text(c.name or "", color=COLORS["text_primary"], size=13)),
                    ft.DataCell(ft.Text(c.email or "", color=COLORS["text_secondary"], size=12)),
                    ft.DataCell(ft.Text(c.phone or "", color=COLORS["text_secondary"], size=12)),
                    ft.DataCell(ft.Row([
                        ft.IconButton(ft.Icons.EDIT, icon_color=COLORS["info"], icon_size=18,
                                     tooltip="Editar", on_click=lambda e, cid=c.id: self._edit_customer(cid)),
                        ft.IconButton(ft.Icons.DELETE, icon_color=COLORS["danger"], icon_size=18,
                                     tooltip="Eliminar", on_click=lambda e, cid=c.id: self._delete_customer(cid)),
                    ], spacing=0)),
                ],
            ))
        
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("NIT/CC", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Nombre", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Email", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Teléfono", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Acciones", color=COLORS["text_secondary"], size=12)),
            ],
            rows=rows,
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            heading_row_color=COLORS["bg_secondary"],
            data_row_max_height=50,
        )

    def _build_pagination(self) -> ft.Row:
        total_pages = max(1, (self.total_customers + self.per_page - 1) // self.per_page)
        return ft.Row([
            ft.Text(f"Total: {self.total_customers}", color=COLORS["text_secondary"], size=12),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=self._prev_page,
                         disabled=self.current_page <= 1, icon_color=COLORS["text_secondary"]),
            ft.Text(f"Página {self.current_page} de {total_pages}", color=COLORS["text_primary"], size=13),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=self._next_page,
                         disabled=self.current_page >= total_pages, icon_color=COLORS["text_secondary"]),
        ], alignment=ft.MainAxisAlignment.CENTER)

    def _on_tab_change(self, e):
        idx = e.control.selected_index
        self.show_type = ["all", "customer", "supplier"][idx]
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
        total_pages = max(1, (self.total_customers + self.per_page - 1) // self.per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self._refresh()

    def _refresh(self):
        self._load_customers()
        self.table_container.content = self._build_table()
        self.pagination.controls = self._build_pagination().controls
        self.page.update()

    def _show_form(self, e, customer_id=None):
        """Mostrar formulario de cliente"""
        from services import ApiDianService
        
        customer = None
        if customer_id:
            session = get_session()
            customer = session.query(Customer).get(customer_id)
            session.close()
        
        # Campos del formulario
        fields = {}
        fields["type"] = dropdown("Tipo", customer.type if customer else "customer", [
            ft.dropdown.Option("customer", "Cliente"),
            ft.dropdown.Option("supplier", "Proveedor"),
        ], width=200)
        fields["type_document_identification_id"] = dropdown("Tipo Doc.", 
            str(customer.type_document_identification_id if customer else 3),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_documents"].items()], width=250)
        fields["identification_number"] = text_field("Número de Documento", 
            customer.identification_number if customer else "", width=180)
        fields["dv"] = text_field("DV", customer.dv if customer else "", width=60)
        fields["name"] = text_field("Razón Social / Nombre", customer.name if customer else "")
        fields["trade_name"] = text_field("Nombre Comercial", customer.trade_name if customer else "")
        fields["email"] = text_field("Email", customer.email if customer else "", width=250)
        fields["phone"] = text_field("Teléfono", customer.phone if customer else "", width=150)
        fields["address"] = text_field("Dirección", customer.address if customer else "")
        fields["type_organization_id"] = dropdown("Tipo Organización",
            str(customer.type_organization_id if customer else 2),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_organizations"].items()], width=280)
        fields["type_regime_id"] = dropdown("Régimen",
            str(customer.type_regime_id if customer else 2),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_regimes"].items()], width=220)
        fields["type_liability_id"] = dropdown("Responsabilidad",
            str(customer.type_liability_id if customer else 117),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_liabilities"].items()], width=300)
        
        # Indicador de carga para consulta DIAN
        loading_indicator = ft.ProgressRing(width=16, height=16, stroke_width=2, visible=False)
        
        def search_dian(e):
            """Consultar tercero en la DIAN"""
            doc_type = fields["type_document_identification_id"].value
            doc_number = fields["identification_number"].value
            
            if not doc_type or not doc_number:
                snackbar(self.page, "Ingrese tipo y número de documento", "warning")
                return
            
            loading_indicator.visible = True
            self.page.update()
            
            try:
                service = ApiDianService()
                result = service.get_acquirer(int(doc_type), doc_number)
                
                if result.get("success"):
                    name = result.get("name", "")
                    email = result.get("email", "")
                    
                    if name:
                        fields["name"].value = name
                    if email:
                        fields["email"].value = email
                    
                    # Calcular DV automáticamente para NIT (tipo 6)
                    if doc_type == "6":
                        dv = service._calculate_dv(doc_number)
                        fields["dv"].value = dv
                    
                    self.page.update()
                    snackbar(self.page, "Datos encontrados en DIAN", "success")
                else:
                    snackbar(self.page, result.get("message", "No se encontró información"), "warning")
            except Exception as ex:
                snackbar(self.page, f"Error: {str(ex)}", "danger")
            finally:
                loading_indicator.visible = False
                self.page.update()
        
        def save_customer(e):
            session = get_session()
            if customer_id:
                c = session.query(Customer).get(customer_id)
            else:
                c = Customer()
                session.add(c)
            
            c.type = fields["type"].value
            c.type_document_identification_id = int(fields["type_document_identification_id"].value or 3)
            c.identification_number = fields["identification_number"].value
            c.dv = fields["dv"].value
            c.name = fields["name"].value
            c.trade_name = fields["trade_name"].value
            c.email = fields["email"].value
            c.phone = fields["phone"].value
            c.address = fields["address"].value
            c.type_organization_id = int(fields["type_organization_id"].value or 2)
            c.type_regime_id = int(fields["type_regime_id"].value or 2)
            c.type_liability_id = int(fields["type_liability_id"].value or 117)
            
            session.commit()
            session.close()
            
            dlg.open = False
            self.page.update()
            self._refresh()
            snackbar(self.page, "Cliente guardado correctamente", "success")
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        # Botón de búsqueda DIAN
        search_btn = ft.IconButton(
            ft.Icons.SEARCH,
            icon_color=COLORS["primary"],
            tooltip="Consultar en DIAN",
            on_click=search_dian,
        )
        
        dlg = ft.AlertDialog(
            title=ft.Text("Editar Cliente" if customer_id else "Nuevo Cliente", 
                         size=18, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([fields["type"], fields["type_document_identification_id"]], spacing=12),
                    ft.Row([
                        fields["identification_number"], 
                        fields["dv"],
                        search_btn,
                        loading_indicator,
                    ], spacing=8),
                    fields["name"],
                    fields["trade_name"],
                    ft.Row([fields["email"], fields["phone"]], spacing=12),
                    fields["address"],
                    fields["type_organization_id"],
                    ft.Row([fields["type_regime_id"], fields["type_liability_id"]], spacing=12, wrap=True),
                ], spacing=12, scroll=ft.ScrollMode.AUTO),
                width=550, height=450,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Guardar", on_click=save_customer, bgcolor=COLORS["success"], color="white"),
            ],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _edit_customer(self, customer_id):
        self._show_form(None, customer_id)

    def _delete_customer(self, customer_id):
        def confirm_delete(e):
            session = get_session()
            c = session.query(Customer).get(customer_id)
            if c:
                session.delete(c)
                session.commit()
            session.close()
            dlg.open = False
            self.page.update()
            self._refresh()
            snackbar(self.page, "Cliente eliminado", "success")
        
        def cancel_delete(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar eliminación", color=COLORS["danger"]),
            content=ft.Text("¿Está seguro de eliminar este cliente?", color=COLORS["text_primary"]),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_delete),
                ft.ElevatedButton("Eliminar", on_click=confirm_delete, bgcolor=COLORS["danger"], color="white"),
            ],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
