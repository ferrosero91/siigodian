"""Vista de Productos/Servicios"""
import flet as ft
from database import get_session, Product
from views.theme import COLORS, button, text_field, dropdown, section_title, divider, snackbar


class ProductsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.products = []
        self.search_text = ""
        self.current_page = 1
        self.per_page = 15

    def _load_products(self):
        session = get_session()
        query = session.query(Product).filter(Product.is_active == True)
        
        if self.search_text:
            search = f"%{self.search_text}%"
            query = query.filter(
                (Product.code.like(search)) |
                (Product.name.like(search))
            )
        
        self.total_products = query.count()
        self.products = query.order_by(Product.name).offset((self.current_page - 1) * self.per_page).limit(self.per_page).all()
        session.close()

    def build(self) -> ft.Container:
        self._load_products()
        
        # Buscador
        self.search_field = ft.TextField(
            hint_text="Buscar por código o nombre...",
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
            ft.Icon(ft.Icons.INVENTORY_2, color=COLORS["primary"], size=28),
            ft.Text("Productos y Servicios", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"]),
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
                divider(),
                self.table_container,
                self.pagination,
            ], expand=True, spacing=10),
            expand=True, padding=24, bgcolor=COLORS["bg_primary"],
        )

    def _build_table(self) -> ft.DataTable:
        rows = []
        for p in self.products:
            tax_color = COLORS["success"] if p.tax_percent == 0 else (COLORS["warning"] if p.tax_percent == 5 else COLORS["info"])
            
            rows.append(ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(p.code or "", color=COLORS["primary"], size=13, weight=ft.FontWeight.W_500)),
                    ft.DataCell(ft.Container(
                        content=ft.Text(p.name or "", color=COLORS["text_primary"], size=13),
                        width=250,
                    )),
                    ft.DataCell(ft.Text(f"$ {p.unit_price:,.0f}", color=COLORS["text_primary"], size=13)),
                    ft.DataCell(ft.Container(
                        content=ft.Text(f"{p.tax_percent:.0f}%", color="white", size=11),
                        bgcolor=tax_color,
                        padding=ft.padding.symmetric(horizontal=8, vertical=4),
                        border_radius=4,
                    )),
                    ft.DataCell(ft.Text(f"{p.stock:,.0f}", color=COLORS["text_secondary"], size=13)),
                    ft.DataCell(ft.Row([
                        ft.IconButton(ft.Icons.EDIT, icon_color=COLORS["info"], icon_size=18,
                                     tooltip="Editar", on_click=lambda e, pid=p.id: self._edit_product(pid)),
                        ft.IconButton(ft.Icons.DELETE, icon_color=COLORS["danger"], icon_size=18,
                                     tooltip="Eliminar", on_click=lambda e, pid=p.id: self._delete_product(pid)),
                    ], spacing=0)),
                ],
            ))
        
        return ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Nombre", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Precio", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("IVA", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Stock", color=COLORS["text_secondary"], size=12)),
                ft.DataColumn(ft.Text("Acciones", color=COLORS["text_secondary"], size=12)),
            ],
            rows=rows,
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            heading_row_color=COLORS["bg_secondary"],
            data_row_max_height=50,
        )

    def _build_pagination(self) -> ft.Row:
        total_pages = max(1, (self.total_products + self.per_page - 1) // self.per_page)
        return ft.Row([
            ft.Text(f"Total: {self.total_products}", color=COLORS["text_secondary"], size=12),
            ft.Container(expand=True),
            ft.IconButton(ft.Icons.CHEVRON_LEFT, on_click=self._prev_page,
                         disabled=self.current_page <= 1, icon_color=COLORS["text_secondary"]),
            ft.Text(f"Página {self.current_page} de {total_pages}", color=COLORS["text_primary"], size=13),
            ft.IconButton(ft.Icons.CHEVRON_RIGHT, on_click=self._next_page,
                         disabled=self.current_page >= total_pages, icon_color=COLORS["text_secondary"]),
        ], alignment=ft.MainAxisAlignment.CENTER)

    def _on_search(self, e):
        self.search_text = e.control.value
        self.current_page = 1
        self._refresh()

    def _prev_page(self, e):
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh()

    def _next_page(self, e):
        total_pages = max(1, (self.total_products + self.per_page - 1) // self.per_page)
        if self.current_page < total_pages:
            self.current_page += 1
            self._refresh()

    def _refresh(self):
        self._load_products()
        self.table_container.content = self._build_table()
        self.pagination.controls = self._build_pagination().controls
        self.page.update()

    def _show_form(self, e, product_id=None):
        """Mostrar formulario de producto"""
        product = None
        if product_id:
            session = get_session()
            product = session.query(Product).get(product_id)
            session.close()
        
        # Campos del formulario
        fields = {}
        fields["code"] = text_field("Código", product.code if product else "", width=150)
        fields["name"] = text_field("Nombre", product.name if product else "")
        fields["description"] = ft.TextField(
            label="Descripción",
            value=product.description if product else "",
            multiline=True,
            min_lines=2,
            max_lines=4,
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            text_style=ft.TextStyle(color=COLORS["text_primary"]),
        )
        fields["unit_price"] = text_field("Precio Unitario", 
            str(product.unit_price) if product else "0", width=150)
        fields["tax_percent"] = dropdown("IVA %", 
            str(int(product.tax_percent)) if product else "0",
            [
                ft.dropdown.Option("0", "0% - Excluido"),
                ft.dropdown.Option("5", "5%"),
                ft.dropdown.Option("19", "19%"),
            ], width=180)
        fields["stock"] = text_field("Stock", str(product.stock) if product else "0", width=120)
        fields["min_stock"] = text_field("Stock Mínimo", str(product.min_stock) if product else "0", width=120)
        fields["unit_measure_id"] = dropdown("Unidad de Medida",
            str(product.unit_measure_id) if product else "70",
            [
                ft.dropdown.Option("70", "Unidad (UN)"),
                ft.dropdown.Option("94", "Docena (DOC)"),
                ft.dropdown.Option("36", "Mes (MON)"),
                ft.dropdown.Option("26", "Tonelada (TNE)"),
                ft.dropdown.Option("17", "Kilogramo (KGM)"),
                ft.dropdown.Option("18", "Gramo (GRM)"),
                ft.dropdown.Option("19", "Litro (LTR)"),
                ft.dropdown.Option("20", "Mililitro (MLT)"),
                ft.dropdown.Option("21", "Metro (MTR)"),
                ft.dropdown.Option("22", "Centímetro (CMT)"),
            ], width=200)
        
        def save_product(e):
            session = get_session()
            if product_id:
                p = session.query(Product).get(product_id)
            else:
                p = Product()
                session.add(p)
            
            p.code = fields["code"].value
            p.name = fields["name"].value
            p.description = fields["description"].value
            p.unit_price = float(fields["unit_price"].value or 0)
            p.tax_percent = float(fields["tax_percent"].value or 0)
            p.stock = float(fields["stock"].value or 0)
            p.min_stock = float(fields["min_stock"].value or 0)
            p.unit_measure_id = int(fields["unit_measure_id"].value or 70)
            
            session.commit()
            session.close()
            
            dlg.open = False
            self.page.update()
            self._refresh()
            snackbar(self.page, "Producto guardado correctamente", "success")
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Editar Producto" if product_id else "Nuevo Producto", 
                         size=18, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([fields["code"], fields["unit_measure_id"]], spacing=12),
                    fields["name"],
                    fields["description"],
                    ft.Row([fields["unit_price"], fields["tax_percent"]], spacing=12),
                    ft.Row([fields["stock"], fields["min_stock"]], spacing=12),
                ], spacing=16, scroll=ft.ScrollMode.AUTO),
                width=450, height=380,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Guardar", on_click=save_product, bgcolor=COLORS["success"], color="white"),
            ],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _edit_product(self, product_id):
        self._show_form(None, product_id)

    def _delete_product(self, product_id):
        def confirm_delete(e):
            session = get_session()
            p = session.query(Product).get(product_id)
            if p:
                p.is_active = False  # Soft delete
                session.commit()
            session.close()
            dlg.open = False
            self.page.update()
            self._refresh()
            snackbar(self.page, "Producto eliminado", "success")
        
        def cancel_delete(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar eliminación", color=COLORS["danger"]),
            content=ft.Text("¿Está seguro de eliminar este producto?", color=COLORS["text_primary"]),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_delete),
                ft.ElevatedButton("Eliminar", on_click=confirm_delete, bgcolor=COLORS["danger"], color="white"),
            ],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()
