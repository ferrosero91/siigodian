"""Vista de documentos"""
import flet as ft
from datetime import datetime, date, timedelta
from database import get_session, Document, Resolution
from services import ApiDianService, FolderWatcherService
from views.theme import COLORS, button, status_badge, type_badge, snackbar, dropdown, text_field


class DocumentsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.current_tab = "all"
        self.search_text = ""
        self.current_page = 1
        self.per_page = 20
        self.total_pages = 1
        self.total_docs = 0
        self.date_filter = "all"  # all, today, week, month, year, custom
        self.date_from = None
        self.date_to = None
        self.documents_list = ft.ListView(expand=True, spacing=1)
        self.pagination_info = ft.Text("", size=12, color=COLORS["text_secondary"])
        self.search_field = ft.TextField(
            hint_text="Buscar...",
            width=180,
            height=38,
            text_size=13,
            content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
            bgcolor=COLORS["bg_primary"],
            border_color=COLORS["border"],
            color=COLORS["text_primary"],
            prefix_icon=ft.Icons.SEARCH,
            on_change=self._on_search,
        )
        self.date_dropdown = ft.Dropdown(
            value="all",
            width=130,
            height=38,
            text_size=12,
            content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
            bgcolor=COLORS["bg_primary"],
            border_color=COLORS["border"],
            color=COLORS["text_primary"],
            options=[
                ft.dropdown.Option("all", "Todas"),
                ft.dropdown.Option("today", "Hoy"),
                ft.dropdown.Option("week", "Esta semana"),
                ft.dropdown.Option("month", "Este mes"),
                ft.dropdown.Option("year", "Este año"),
                ft.dropdown.Option("custom", "Rango..."),
            ],
            on_change=self._on_date_filter_change,
        )
        self.tabs = ft.Tabs(
            selected_index=0,
            on_change=self._on_tab_change,
            height=42,
            tabs=[
                ft.Tab(text="Todos"),
                ft.Tab(text="Facturas"),
                ft.Tab(text="NC"),
                ft.Tab(text="ND"),
                ft.Tab(text="Pendientes"),
            ],
            indicator_color=COLORS["primary"],
            label_color=COLORS["text_primary"],
            unselected_label_color=COLORS["text_secondary"],
        )

    def build_navbar(self) -> ft.Row:
        """Construir la barra de navegación con tabs, búsqueda, filtro de fechas y acciones"""
        return ft.Row([
            self.tabs,
            ft.Container(width=5),
            self.search_field,
            self.date_dropdown,
            ft.Container(expand=True),
            ft.IconButton(icon=ft.Icons.FOLDER_OPEN, icon_color=COLORS["primary"], tooltip="Escanear carpeta", icon_size=22, on_click=self._scan_folder),
            ft.IconButton(icon=ft.Icons.SEND, icon_color=COLORS["success"], tooltip="Enviar Pendientes", icon_size=22, on_click=self._send_pending),
            ft.IconButton(icon=ft.Icons.REFRESH, icon_color=COLORS["info"], tooltip="Actualizar", icon_size=22, on_click=self._refresh),
            ft.Container(width=10),
        ], spacing=4, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _build_pagination(self) -> ft.Container:
        """Construir controles de paginación"""
        self.pagination_container = ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.Icons.FIRST_PAGE, icon_size=20,
                    icon_color=COLORS["primary"],
                    tooltip="Primera página",
                    on_click=lambda e: self._go_to_page(1),
                ),
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_LEFT, icon_size=20,
                    icon_color=COLORS["primary"],
                    tooltip="Anterior",
                    on_click=lambda e: self._go_to_page(self.current_page - 1),
                ),
                self.pagination_info,
                ft.IconButton(
                    icon=ft.Icons.CHEVRON_RIGHT, icon_size=20,
                    icon_color=COLORS["primary"],
                    tooltip="Siguiente",
                    on_click=lambda e: self._go_to_page(self.current_page + 1),
                ),
                ft.IconButton(
                    icon=ft.Icons.LAST_PAGE, icon_size=20,
                    icon_color=COLORS["primary"],
                    tooltip="Última página",
                    on_click=lambda e: self._go_to_page(self.total_pages),
                ),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            padding=ft.padding.symmetric(vertical=8),
            bgcolor=COLORS["bg_secondary"],
            border_radius=ft.border_radius.only(bottom_left=8, bottom_right=8),
        )
        return self.pagination_container

    def _go_to_page(self, page: int):
        """Ir a una página específica"""
        if 1 <= page <= self.total_pages and page != self.current_page:
            self.current_page = page
            self._load_documents()

    def build(self) -> ft.Container:
        content = ft.Column([
            ft.Container(content=self.documents_list, expand=True, bgcolor=COLORS["bg_primary"]),
            self._build_pagination(),
        ], expand=True, spacing=0)
        self._load_documents()
        return ft.Container(content=content, expand=True, padding=ft.padding.only(left=16, right=16, top=8, bottom=16), bgcolor=COLORS["bg_primary"])

    def _on_search(self, e):
        self.search_text = e.control.value.strip().lower()
        self.current_page = 1  # Reset a primera página al buscar
        self._load_documents()

    def _on_tab_change(self, e):
        tab_map = {0: "all", 1: "invoice", 2: "credit_note", 3: "debit_note", 4: "pending"}
        self.current_tab = tab_map.get(e.control.selected_index, "all")
        self.current_page = 1  # Reset a primera página al cambiar tab
        self._load_documents()

    def _on_date_filter_change(self, e):
        """Manejar cambio en filtro de fecha"""
        self.date_filter = e.control.value
        today = date.today()
        
        if self.date_filter == "all":
            self.date_from = None
            self.date_to = None
        elif self.date_filter == "today":
            self.date_from = today
            self.date_to = today
        elif self.date_filter == "week":
            self.date_from = today - timedelta(days=today.weekday())
            self.date_to = today
        elif self.date_filter == "month":
            self.date_from = today.replace(day=1)
            self.date_to = today
        elif self.date_filter == "year":
            self.date_from = today.replace(month=1, day=1)
            self.date_to = today
        elif self.date_filter == "custom":
            self._show_date_range_dialog()
            return
        
        self.current_page = 1
        self._load_documents()

    def _show_date_range_dialog(self):
        """Mostrar diálogo para seleccionar rango de fechas"""
        today = date.today()
        
        # Campos de fecha
        from_field = ft.TextField(
            label="Desde",
            value=self.date_from.strftime("%Y-%m-%d") if self.date_from else today.replace(day=1).strftime("%Y-%m-%d"),
            width=150,
            height=50,
            text_size=13,
            hint_text="YYYY-MM-DD",
            bgcolor=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            color=COLORS["text_primary"],
        )
        to_field = ft.TextField(
            label="Hasta",
            value=self.date_to.strftime("%Y-%m-%d") if self.date_to else today.strftime("%Y-%m-%d"),
            width=150,
            height=50,
            text_size=13,
            hint_text="YYYY-MM-DD",
            bgcolor=COLORS["bg_secondary"],
            border_color=COLORS["border"],
            color=COLORS["text_primary"],
        )
        
        def apply_filter(e):
            try:
                self.date_from = datetime.strptime(from_field.value, "%Y-%m-%d").date()
                self.date_to = datetime.strptime(to_field.value, "%Y-%m-%d").date()
                self.current_page = 1
                dlg.open = False
                self.page.update()
                self._load_documents()
            except ValueError:
                snackbar(self.page, "Formato de fecha inválido. Use YYYY-MM-DD", "warning")
        
        def cancel(e):
            self.date_dropdown.value = "all"
            self.date_filter = "all"
            self.date_from = None
            self.date_to = None
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Text("Seleccionar rango de fechas", size=16, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([from_field, to_field], spacing=16),
                    ft.Text("Formato: YYYY-MM-DD (ej: 2025-12-29)", size=11, color=COLORS["text_secondary"]),
                ], spacing=12),
                width=350,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel),
                ft.ElevatedButton(
                    text="Aplicar",
                    on_click=apply_filter,
                    bgcolor=COLORS["primary"],
                    color="#ffffff",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _load_documents(self):
        session = get_session()
        query = session.query(Document)
        
        # SIEMPRE excluir documentos soporte (se ven en Compras)
        query = query.filter(Document.type.notin_(["support_document", "sd_adjustment_note"]))
        
        if self.current_tab == "invoice":
            query = query.filter(Document.type == "invoice")
        elif self.current_tab == "credit_note":
            query = query.filter(Document.type == "credit_note")
        elif self.current_tab == "debit_note":
            query = query.filter(Document.type == "debit_note")
        elif self.current_tab == "pending":
            query = query.filter(Document.status == "pending")
        
        # Aplicar filtro de fechas
        if self.date_from:
            from sqlalchemy import func
            query = query.filter(func.date(Document.issue_date) >= self.date_from)
        if self.date_to:
            from sqlalchemy import func
            query = query.filter(func.date(Document.issue_date) <= self.date_to)
        
        # Aplicar búsqueda si hay texto
        if self.search_text:
            search_pattern = f"%{self.search_text}%"
            query = query.filter(
                (Document.full_number.ilike(search_pattern)) |
                (Document.customer_name.ilike(search_pattern)) |
                (Document.customer_nit.ilike(search_pattern))
            )
        
        # Contar total para paginación
        self.total_docs = query.count()
        self.total_pages = max(1, (self.total_docs + self.per_page - 1) // self.per_page)
        
        # Asegurar que la página actual es válida
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        
        # Aplicar paginación
        offset = (self.current_page - 1) * self.per_page
        docs = query.order_by(Document.status != "pending", Document.id.desc()).offset(offset).limit(self.per_page).all()
        session.close()
        
        # Actualizar info de paginación
        start = offset + 1 if self.total_docs > 0 else 0
        end = min(offset + self.per_page, self.total_docs)
        self.pagination_info.value = f"{start}-{end} de {self.total_docs}"
        
        self.documents_list.controls.clear()
        header = ft.Container(
            content=ft.Row([
                ft.Text("Número", width=130, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Tipo", width=90, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Cliente", width=280, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Total", width=110, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Estado", width=90, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Acciones", expand=True, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=COLORS["bg_secondary"],
            border_radius=ft.border_radius.only(top_left=8, top_right=8),
        )
        self.documents_list.controls.append(header)
        for doc in docs:
            self.documents_list.controls.append(self._build_row(doc))
        self.page.update()

    def _build_row(self, doc: Document) -> ft.Container:
        actions = []
        # Botón ver detalles siempre visible
        actions.append(ft.IconButton(icon=ft.Icons.VISIBILITY, icon_color=COLORS["text_secondary"], tooltip="Ver detalles", icon_size=20,
            on_click=lambda e, d=doc: self._show_details_dialog(d)))
        
        if doc.status == "pending":
            actions.append(ft.IconButton(icon=ft.Icons.SEND, icon_color=COLORS["primary"], tooltip="Enviar", icon_size=20,
                on_click=lambda e, d=doc: self._send_document(d)))
            actions.append(ft.IconButton(icon=ft.Icons.DELETE, icon_color=COLORS["danger"], tooltip="Eliminar", icon_size=20,
                on_click=lambda e, d=doc: self._delete_document(d)))
        if doc.status == "sent":
            # PDF: verde si ya se descargó, rojo si no
            pdf_color = "#10b981" if doc.pdf_downloaded else "#ef4444"
            pdf_tooltip = "PDF descargado ✓" if doc.pdf_downloaded else "Descargar PDF"
            # Email: verde si ya se envió, violeta si no
            email_color = "#10b981" if doc.email_sent else "#8b5cf6"
            email_tooltip = "Email enviado ✓" if doc.email_sent else "Enviar Email"
            
            actions.extend([
                ft.IconButton(icon=ft.Icons.PICTURE_AS_PDF, icon_color=pdf_color, tooltip=pdf_tooltip, icon_size=20,
                    on_click=lambda e, d=doc: self._download_pdf(d)),
                ft.IconButton(icon=ft.Icons.PRINT, icon_color="#ec4899", tooltip="Imprimir Ticket 80mm", icon_size=20,
                    on_click=lambda e, d=doc: self._print_ticket(d)),
                ft.IconButton(icon=ft.Icons.EMAIL, icon_color=email_color, tooltip=email_tooltip, icon_size=20,
                    on_click=lambda e, d=doc: self._send_email(d)),
            ])
            if doc.type == "invoice":
                actions.extend([
                    ft.IconButton(icon=ft.Icons.REMOVE_CIRCLE, icon_color="#f59e0b", tooltip="Crear Nota Crédito", icon_size=20,
                        on_click=lambda e, d=doc: self._show_nc_dialog(d)),
                    ft.IconButton(icon=ft.Icons.ADD_CIRCLE, icon_color="#06b6d4", tooltip="Crear Nota Débito", icon_size=20,
                        on_click=lambda e, d=doc: self._show_nd_dialog(d)),
                ])
        if doc.status == "error":
            actions.extend([
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=COLORS["warning"], tooltip="Reintentar envío", icon_size=20,
                    on_click=lambda e, d=doc: self._retry_document(d)),
                ft.IconButton(icon=ft.Icons.ERROR_OUTLINE, icon_color=COLORS["danger"], tooltip="Ver error", icon_size=20,
                    on_click=lambda e, d=doc: self._show_error_dialog(d)),
            ])
        if doc.status == "rejected":
            actions.extend([
                ft.IconButton(icon=ft.Icons.REFRESH, icon_color=COLORS["warning"], tooltip="Reintentar envío", icon_size=20,
                    on_click=lambda e, d=doc: self._retry_document(d)),
                ft.IconButton(icon=ft.Icons.ERROR_OUTLINE, icon_color=COLORS["danger"], tooltip="Ver rechazo DIAN", icon_size=20,
                    on_click=lambda e, d=doc: self._show_error_dialog(d)),
            ])
        return ft.Container(
            content=ft.Row([
                ft.Text(doc.full_number or "", width=130, 
                       color="#ef4444" if getattr(doc, 'is_nullified', False) else COLORS["text_primary"], 
                       size=13,
                       style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if getattr(doc, 'is_nullified', False) else None),
                ft.Container(content=type_badge(doc.type), width=90),
                ft.Text(doc.customer_name or "", width=280, 
                       color="#ef4444" if getattr(doc, 'is_nullified', False) else COLORS["text_primary"], 
                       size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"$ {doc.total:,.0f}", width=110, 
                       color="#ef4444" if getattr(doc, 'is_nullified', False) else COLORS["text_primary"], 
                       size=13),
                ft.Container(content=status_badge(doc.status) if not getattr(doc, 'is_nullified', False) else ft.Container(
                    content=ft.Text("Anulada", color="white", size=11),
                    bgcolor="#ef4444",
                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                    border_radius=4,
                ), width=90),
                ft.Row(actions, expand=True, spacing=0),
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            bgcolor=COLORS["bg_card"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
            on_hover=lambda e: self._on_hover(e),
        )

    def _on_hover(self, e):
        try:
            if e.control.page:  # Solo actualizar si el control está en la página
                e.control.bgcolor = COLORS["bg_hover"] if e.data == "true" else COLORS["bg_card"]
                e.control.update()
        except:
            pass  # Ignorar errores de hover en controles no montados

    def _delete_document(self, doc: Document):
        """Eliminar documento pendiente de la base de datos"""
        def confirm_delete(e):
            session = get_session()
            d = session.query(Document).get(doc.id)
            if d and d.status == "pending":
                session.delete(d)
                session.commit()
                snackbar(self.page, f"Documento {doc.full_number} eliminado", "success")
            else:
                snackbar(self.page, "Solo se pueden eliminar documentos pendientes", "warning")
            session.close()
            dlg.open = False
            self.page.update()
            self._load_documents()
        
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.DELETE_FOREVER, color=COLORS["danger"]),
                ft.Text(f"Eliminar {doc.full_number}", size=16, weight=ft.FontWeight.W_600),
            ], spacing=10),
            content=ft.Text(f"¿Está seguro de eliminar este documento?\nEsta acción no se puede deshacer.", color=COLORS["text_secondary"]),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close(dlg)),
                ft.ElevatedButton(
                    text="Eliminar",
                    on_click=confirm_delete,
                    bgcolor=COLORS["danger"],
                    color="#ffffff",
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _retry_document(self, doc: Document):
        """Reintentar envío de documento con error"""
        # Primero cambiar estado a pending para poder reenviar
        session = get_session()
        d = session.query(Document).get(doc.id)
        d.status = "pending"
        d.error_message = None
        session.commit()
        session.close()
        
        # Ahora enviar
        self._send_document(doc)

    def _show_error_dialog(self, doc: Document):
        """Mostrar diálogo con detalles del error o rechazo DIAN"""
        import json
        
        error_msg = doc.error_message or "Sin mensaje de error"
        api_response = doc.api_response or {}
        is_rejected = doc.status == "rejected"
        
        # Intentar extraer más detalles del error
        error_details = ""
        if api_response:
            if "message" in api_response:
                error_details += f"Mensaje: {api_response['message']}\n"
            if "errors" in api_response:
                error_details += f"Errores: {json.dumps(api_response['errors'], indent=2, ensure_ascii=False)}\n"
            if "ResponseDian" in api_response:
                dian_response = api_response.get("ResponseDian", {})
                if isinstance(dian_response, dict):
                    error_details += f"\nRespuesta DIAN:\n{json.dumps(dian_response, indent=2, ensure_ascii=False)}"
        
        # Título según el tipo de error
        title_text = f"Rechazado por DIAN - {doc.full_number}" if is_rejected else f"Error en {doc.full_number}"
        title_icon = ft.Icons.BLOCK if is_rejected else ft.Icons.ERROR
        
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(title_icon, color=COLORS["danger"]),
                ft.Text(title_text, size=18, weight=ft.FontWeight.W_600),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Motivo del rechazo:" if is_rejected else "Mensaje de error:", weight=ft.FontWeight.W_600, color=COLORS["text_secondary"]),
                    ft.Container(
                        content=ft.Text(error_msg, color=COLORS["danger"], selectable=True),
                        bgcolor=COLORS["bg_secondary"],
                        padding=12,
                        border_radius=8,
                    ),
                    ft.Divider(color=COLORS["border"]) if error_details else ft.Container(),
                    ft.Text("Detalles técnicos:", weight=ft.FontWeight.W_600, color=COLORS["text_secondary"]) if error_details else ft.Container(),
                    ft.TextField(
                        value=error_details or "Sin detalles adicionales",
                        multiline=True, read_only=True, min_lines=6, max_lines=12,
                        text_size=10, bgcolor=COLORS["bg_secondary"],
                        border_color=COLORS["border"], color=COLORS["text_primary"],
                    ) if error_details else ft.Container(),
                ], spacing=10, scroll=ft.ScrollMode.AUTO),
                width=550, height=350,
            ),
            actions=[
                ft.TextButton("Cerrar", on_click=lambda e: self._close(dlg)),
                ft.ElevatedButton(
                    text="Reintentar Envío",
                    on_click=lambda e: self._retry_and_close(doc, dlg),
                    bgcolor=COLORS["warning"],
                    color="#ffffff",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _retry_and_close(self, doc: Document, dlg):
        """Reintentar y cerrar diálogo"""
        dlg.open = False
        self.page.update()
        self._retry_document(doc)

    def _scan_folder(self, e):
        service = FolderWatcherService()
        results = service.scan()
        snackbar(self.page, f"Procesados: {results['processed']}, Errores: {results['errors']}", "success" if results['errors'] == 0 else "warning")
        self._load_documents()

    def _send_document(self, doc: Document):
        session = get_session()
        d = session.query(Document).get(doc.id)
        d.status = "processing"
        doc_type = d.type
        reference_document_id = d.reference_document_id
        session.commit()
        session.close()
        self._load_documents()
        service = ApiDianService()
        if doc.type == "invoice":
            result = service.send_invoice(doc)
        elif doc.type == "credit_note":
            result = service.send_credit_note(doc)
        elif doc.type == "debit_note":
            result = service.send_debit_note(doc)
        else:
            result = {"success": False, "message": "Tipo no soportado"}
        
        # Recargar documento para obtener estado actualizado
        session = get_session()
        updated_doc = session.query(Document).get(doc.id)
        final_status = updated_doc.status if updated_doc else "error"
        error_msg = updated_doc.error_message if updated_doc else None
        
        # Si es NC y se envió exitosamente, marcar la factura original como anulada
        if doc_type == "credit_note" and final_status == "sent" and reference_document_id:
            ref_doc = session.query(Document).get(reference_document_id)
            if ref_doc:
                ref_doc.is_nullified = True
        
        session.commit()
        session.close()
        
        if final_status == "sent":
            snackbar(self.page, "Procesado Correctamente", "success")
        elif final_status == "rejected":
            snackbar(self.page, f"Rechazado: {error_msg[:80] if error_msg else 'Ver detalles'}", "danger")
        elif result.get("success"):
            snackbar(self.page, "Documento enviado a la DIAN", "success")
        else:
            snackbar(self.page, f"Error: {result.get('message', 'Error')}", "danger")
        self._load_documents()

    def _send_pending(self, e):
        session = get_session()
        pending = session.query(Document).filter(Document.status == "pending").all()
        session.close()
        if not pending:
            snackbar(self.page, "No hay documentos pendientes", "warning")
            return
        for doc in pending:
            self._send_document(doc)

    def _download_pdf(self, doc: Document):
        service = ApiDianService()
        result = service.download_pdf(doc)
        if result.get("success"):
            import os
            filepath = os.path.join(os.path.expanduser("~/Downloads"), f"{doc.full_number}.pdf")
            with open(filepath, "wb") as f:
                f.write(result["content"])
            # Marcar como descargado
            session = get_session()
            d = session.query(Document).get(doc.id)
            d.pdf_downloaded = True
            d.pdf_downloaded_at = datetime.now()
            session.commit()
            session.close()
            snackbar(self.page, f"PDF guardado: {filepath}", "success")
            self._load_documents()
        else:
            snackbar(self.page, f"Error: {result.get('message')}", "danger")

    def _send_email(self, doc: Document):
        """Mostrar diálogo para enviar email con opción de cambiar correo"""
        # Obtener datos del documento
        session = get_session()
        document = session.query(Document).get(doc.id)
        current_email = document.customer_email or ""
        doc_full_number = document.full_number
        doc_customer_name = document.customer_name
        doc_id = document.id
        session.close()
        
        # Campo de email editable
        email_field = ft.TextField(
            label="Correo electrónico",
            value=current_email,
            width=400,
            border_color=COLORS["border"],
            focused_border_color=COLORS["primary"],
            label_style=ft.TextStyle(color=COLORS["text_secondary"]),
            text_style=ft.TextStyle(color=COLORS["text_primary"]),
            prefix_icon=ft.Icons.EMAIL,
        )
        
        def do_send_email(e):
            new_email = email_field.value.strip()
            if not new_email:
                snackbar(self.page, "Ingrese un correo electrónico", "warning")
                return
            
            # Actualizar email en el documento si cambió
            session = get_session()
            d = session.query(Document).get(doc_id)
            if d.customer_email != new_email:
                d.customer_email = new_email
                session.commit()
            session.close()
            
            # Recargar documento con email actualizado
            session = get_session()
            updated_doc = session.query(Document).get(doc_id)
            session.close()
            
            # Enviar email
            service = ApiDianService()
            result = service.send_email(updated_doc)
            
            if result.get("success"):
                # Marcar como enviado
                session = get_session()
                d = session.query(Document).get(doc_id)
                d.email_sent = True
                d.email_sent_at = datetime.now()
                session.commit()
                session.close()
                
                dlg.open = False
                self.page.update()
                snackbar(self.page, result.get("message", "Correo enviado"), "success")
                self._load_documents()
            else:
                snackbar(self.page, f"Error: {result.get('message')}", "danger")
        
        def close_dlg(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.EMAIL, color=COLORS["primary"]),
                ft.Text("Enviar por Correo", size=18, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Documento: {doc_full_number}", color=COLORS["text_primary"], size=14),
                    ft.Text(f"Cliente: {doc_customer_name}", color=COLORS["text_secondary"], size=13),
                    ft.Container(height=10),
                    email_field,
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.INFO_OUTLINE, color=COLORS["info"], size=16),
                            ft.Text("Se enviará el PDF y XML del documento", color=COLORS["text_secondary"], size=12),
                        ], spacing=8),
                        padding=ft.padding.only(top=10),
                    ),
                ], spacing=8),
                width=450,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=close_dlg),
                ft.ElevatedButton("Enviar", on_click=do_send_email, bgcolor=COLORS["success"], color="white", icon=ft.Icons.SEND),
            ],
            bgcolor=COLORS["bg_card"],
        )
        
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _refresh(self, e):
        self._load_documents()

    def _show_nc_dialog(self, invoice: Document):
        """Mostrar diálogo para crear Nota Crédito con selección de productos"""
        # Obtener datos frescos de la factura desde la BD (el objeto puede estar desactualizado)
        session = get_session()
        fresh_invoice = session.query(Document).get(invoice.id)
        parsed_data = fresh_invoice.parsed_data or {}
        lines = parsed_data.get("lines", [])
        customer_data = parsed_data.get("customer", {})
        invoice_customer_nit = fresh_invoice.customer_nit
        invoice_customer_name = fresh_invoice.customer_name
        invoice_customer_email = fresh_invoice.customer_email
        invoice_id = fresh_invoice.id
        invoice_cufe = fresh_invoice.cufe  # CUFE fresco de la BD
        invoice_total = fresh_invoice.total
        invoice_full_number = fresh_invoice.full_number
        session.close()
        
        # Validar que la factura tenga CUFE (necesario para referenciar en la NC)
        if not invoice_cufe:
            snackbar(self.page, f"La factura {invoice_full_number} no tiene CUFE. Debe estar enviada a la DIAN primero.", "danger")
            return
        
        # Crear checkboxes y campos de cantidad para cada producto
        product_checkboxes = []
        quantity_fields = []
        total_labels = []
        
        products_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO)
        
        # Label para mostrar total calculado de la NC
        total_nc_label = ft.Text(f"Total NC: $ {invoice_total:,.0f}", size=14, weight=ft.FontWeight.W_600, color=COLORS["success"])
        
        def update_total(e=None):
            """Recalcular total de la NC cuando cambian cantidades"""
            subtotal = 0
            total_tax = 0
            for i, (cb, qty_field) in enumerate(zip(product_checkboxes, quantity_fields)):
                if cb.value and i < len(lines):
                    try:
                        qty = float(qty_field.value or 0)
                    except:
                        qty = 0
                    if qty > 0:
                        unit_price = float(lines[i].get("unit_price", 0))
                        tax_percent = float(lines[i].get("tax_percent", 0))
                        line_total = qty * unit_price
                        tax_amount = line_total * (tax_percent / 100)
                        subtotal += line_total
                        total_tax += tax_amount
                        # Actualizar label de total de línea
                        if i < len(total_labels):
                            total_labels[i].value = f"$ {line_total:,.0f}"
                            total_labels[i].update()
            total = subtotal + total_tax
            total_nc_label.value = f"Total NC: $ {total:,.0f}"
            total_nc_label.update()
        
        for i, line in enumerate(lines):
            desc = line.get("description", "Producto")[:35]
            qty = float(line.get("quantity", 1))
            price = float(line.get("unit_price", 0))
            total = qty * price
            
            cb = ft.Checkbox(value=True, data=i, on_change=update_total)
            qty_field = ft.TextField(
                value=str(qty), width=70, height=35,
                text_size=12, content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                bgcolor=COLORS["bg_secondary"], border_color=COLORS["border"],
                color=COLORS["text_primary"], on_change=update_total,
            )
            total_label = ft.Text(f"$ {total:,.0f}", width=90, size=12, color=COLORS["text_secondary"], text_align=ft.TextAlign.RIGHT)
            
            product_checkboxes.append(cb)
            quantity_fields.append(qty_field)
            total_labels.append(total_label)
            
            row = ft.Row([
                cb,
                ft.Text(desc, width=150, size=11, color=COLORS["text_primary"], overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"$ {price:,.0f}", width=80, size=11, color=COLORS["text_secondary"], text_align=ft.TextAlign.RIGHT),
                qty_field,
                total_label,
            ], spacing=4)
            products_column.controls.append(row)
        
        disc_dd = dropdown("Motivo", "2", [
            ft.dropdown.Option("1", "1 - Devolución parcial"),
            ft.dropdown.Option("2", "2 - Anulación de factura"),
            ft.dropdown.Option("3", "3 - Rebaja o descuento"),
            ft.dropdown.Option("4", "4 - Ajuste de precio"),
            ft.dropdown.Option("5", "5 - Otros"),
        ], width=450)
        desc_tf = text_field("Descripción", "Anulación de factura electrónica", width=450)
        
        def create(e):
            session = get_session()
            res = session.query(Resolution).filter(Resolution.type_document_id == 4, Resolution.is_active == True).first()
            if not res:
                snackbar(self.page, "No hay resolución de NC activa", "danger")
                dlg.open = False
                self.page.update()
                session.close()
                return
            
            # Filtrar productos seleccionados y calcular totales
            selected_lines = []
            subtotal = 0
            total_tax = 0
            
            for i, (cb, qty_field) in enumerate(zip(product_checkboxes, quantity_fields)):
                if cb.value and i < len(lines):
                    original_line = lines[i]
                    try:
                        qty = float(qty_field.value or 0)
                    except:
                        qty = 0
                    
                    if qty <= 0:
                        continue
                    
                    unit_price = float(original_line.get("unit_price", 0))
                    tax_id = int(original_line.get("tax_id", 1))
                    tax_percent = float(original_line.get("tax_percent", 0))
                    line_total = qty * unit_price
                    tax_amount = line_total * (tax_percent / 100)
                    
                    subtotal += line_total
                    total_tax += tax_amount
                    
                    selected_lines.append({
                        "code": original_line.get("code", str(i + 1)),
                        "description": original_line.get("description", "Producto"),
                        "quantity": qty,
                        "unit_price": unit_price,
                        "total": line_total,
                        "tax_id": tax_id,
                        "tax_percent": tax_percent,
                        "tax_amount": tax_amount,
                    })
            
            if not selected_lines:
                snackbar(self.page, "Seleccione al menos un producto", "warning")
                return
            
            total = subtotal + total_tax
            next_num = res.current_number + 1
            res.current_number = next_num
            
            nc = Document(
                type="credit_note", type_document_id=4, prefix=res.prefix, number=str(next_num),
                full_number=f"{res.prefix}{next_num}", issue_date=datetime.now(),
                customer_nit=invoice_customer_nit, customer_name=invoice_customer_name, customer_email=invoice_customer_email,
                subtotal=subtotal, total_tax=total_tax, total_discount=0, total=total,
                status="pending", xml_content="", xml_filename=f"{res.prefix}{next_num}.xml",
                parsed_data={
                    "customer": customer_data,
                    "lines": selected_lines,
                    "subtotal": subtotal, "total_tax": total_tax, "total": total,
                    "discrepancy_code": disc_dd.value, "discrepancy_description": desc_tf.value
                },
                reference_document_id=invoice_id, reference_cufe=invoice_cufe,
            )
            session.add(nc)
            session.commit()
            nc_full_number = nc.full_number  # Guardar antes de cerrar sesión
            session.close()
            dlg.open = False
            self.page.update()
            snackbar(self.page, f"NC {nc_full_number} creada por $ {total:,.0f}", "success")
            self._load_documents()
        
        # Header de productos
        products_header = ft.Row([
            ft.Text("", width=40),
            ft.Text("Producto", width=150, size=11, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"]),
            ft.Text("Vr. Unit.", width=80, size=11, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], text_align=ft.TextAlign.RIGHT),
            ft.Text("Cant.", width=70, size=11, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"]),
            ft.Text("Total", width=90, size=11, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], text_align=ft.TextAlign.RIGHT),
        ], spacing=4)
        
        dlg = ft.AlertDialog(
            title=ft.Text(f"Crear NC para {invoice_full_number}", size=18, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Cliente: {invoice_customer_name}", color=COLORS["text_secondary"]),
                    ft.Text(f"Total factura: $ {invoice_total:,.0f}", color=COLORS["text_secondary"]),
                    ft.Divider(color=COLORS["border"]),
                    disc_dd, desc_tf,
                    ft.Divider(color=COLORS["border"]),
                    ft.Text("Productos a incluir:", size=13, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
                    products_header,
                    ft.Container(content=products_column, height=180, bgcolor=COLORS["bg_secondary"], border_radius=8, padding=8),
                    ft.Divider(color=COLORS["border"]),
                    total_nc_label,
                ], spacing=10),
                width=550,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close(dlg)),
                ft.ElevatedButton(
                    text="Crear NC",
                    on_click=create,
                    bgcolor=COLORS["warning"],
                    color="#ffffff",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _show_nd_dialog(self, invoice: Document):
        """Mostrar diálogo para crear Nota Débito"""
        # Obtener datos frescos de la factura desde la BD (el objeto puede estar desactualizado)
        session = get_session()
        fresh_invoice = session.query(Document).get(invoice.id)
        parsed_data = fresh_invoice.parsed_data or {}
        customer_data = parsed_data.get("customer", {})
        invoice_customer_nit = fresh_invoice.customer_nit
        invoice_customer_name = fresh_invoice.customer_name
        invoice_customer_email = fresh_invoice.customer_email
        invoice_id = fresh_invoice.id
        invoice_cufe = fresh_invoice.cufe  # CUFE fresco de la BD
        invoice_total = fresh_invoice.total
        invoice_full_number = fresh_invoice.full_number
        session.close()
        
        # Validar que la factura tenga CUFE (necesario para referenciar en la ND)
        if not invoice_cufe:
            snackbar(self.page, f"La factura {invoice_full_number} no tiene CUFE. Debe estar enviada a la DIAN primero.", "danger")
            return
        
        disc_dd = dropdown("Motivo", "3", [
            ft.dropdown.Option("1", "1 - Intereses"),
            ft.dropdown.Option("2", "2 - Gastos por cobrar"),
            ft.dropdown.Option("3", "3 - Cambio del valor"),
            ft.dropdown.Option("4", "4 - Otros"),
        ], width=400)
        amt_tf = text_field("Valor (sin IVA)", "0", width=180)
        tax_tf = text_field("% IVA", "19", width=100)
        con_tf = text_field("Concepto", "Ajuste de valor", width=400)
        
        def create(e):
            session = get_session()
            res = session.query(Resolution).filter(Resolution.type_document_id == 5, Resolution.is_active == True).first()
            if not res:
                snackbar(self.page, "No hay resolución de ND activa", "danger")
                dlg.open = False
                self.page.update()
                session.close()
                return
            
            try:
                subtotal = float(amt_tf.value or 0)
                tax_pct = float(tax_tf.value or 0)
            except:
                snackbar(self.page, "Valores numéricos inválidos", "warning")
                return
            
            if subtotal <= 0:
                snackbar(self.page, "El valor debe ser mayor a 0", "warning")
                return
            
            tax_amt = subtotal * (tax_pct / 100)
            total = subtotal + tax_amt
            next_num = res.current_number + 1
            res.current_number = next_num
            
            nd = Document(
                type="debit_note", type_document_id=5, prefix=res.prefix, number=str(next_num),
                full_number=f"{res.prefix}{next_num}", issue_date=datetime.now(),
                customer_nit=invoice_customer_nit, customer_name=invoice_customer_name, customer_email=invoice_customer_email,
                subtotal=subtotal, total_tax=tax_amt, total_discount=0, total=total,
                status="pending", xml_content="", xml_filename=f"{res.prefix}{next_num}.xml",
                parsed_data={
                    "customer": customer_data,
                    "lines": [{
                        "code": "001",
                        "description": con_tf.value,
                        "quantity": 1,
                        "unit_price": subtotal,
                        "total": subtotal,
                        "tax_id": 1,  # IVA por defecto
                        "tax_percent": tax_pct,
                        "tax_amount": tax_amt
                    }],
                    "subtotal": subtotal, "total_tax": tax_amt, "total": total,
                    "discrepancy_code": disc_dd.value, "discrepancy_description": con_tf.value
                },
                reference_document_id=invoice_id, reference_cufe=invoice_cufe,
            )
            session.add(nd)
            session.commit()
            nd_full_number = nd.full_number  # Guardar antes de cerrar sesión
            session.close()
            dlg.open = False
            self.page.update()
            snackbar(self.page, f"ND {nd_full_number} creada por $ {total:,.0f}", "success")
            self._load_documents()
        
        dlg = ft.AlertDialog(
            title=ft.Text(f"Crear ND para {invoice_full_number}", size=18, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Cliente: {invoice_customer_name}", color=COLORS["text_secondary"]),
                    ft.Text(f"Total factura: $ {invoice_total:,.0f}", color=COLORS["text_secondary"]),
                    ft.Divider(color=COLORS["border"]),
                    disc_dd,
                    ft.Divider(color=COLORS["border"]),
                    ft.Text("Datos de la Nota Débito:", size=13, weight=ft.FontWeight.W_600, color=COLORS["text_primary"]),
                    con_tf,
                    ft.Row([amt_tf, tax_tf], spacing=12),
                ], spacing=10),
                width=450,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close(dlg)),
                ft.ElevatedButton(
                    text="Crear ND",
                    on_click=create,
                    bgcolor=COLORS["info"],
                    color="#ffffff",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _show_details_dialog(self, doc: Document):
        """Mostrar diálogo con detalles del documento"""
        import json
        
        parsed_data = doc.parsed_data or {}
        lines = parsed_data.get("lines", [])
        customer = parsed_data.get("customer", {})
        api_response = doc.api_response or {}
        
        # Construir tabla de productos
        products_rows = []
        for line in lines:
            # Determinar etiqueta de impuesto
            tax_id = int(line.get("tax_id", 1))
            tax_pct = float(line.get("tax_percent", 0))
            if tax_pct == 0:
                tax_label = "Exc"
            elif tax_id == 4:
                tax_label = f"IC {tax_pct:.0f}%"
            else:
                tax_label = f"{tax_pct:.0f}%"
            
            products_rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(line.get("code", "")[:10], size=11)),
                    ft.DataCell(ft.Text(line.get("description", "")[:30], size=11)),
                    ft.DataCell(ft.Text(str(line.get("quantity", 1)), size=11)),
                    ft.DataCell(ft.Text(f"$ {float(line.get('unit_price', 0)):,.0f}", size=11)),
                    ft.DataCell(ft.Text(tax_label, size=11)),
                    ft.DataCell(ft.Text(f"$ {float(line.get('total', 0)):,.0f}", size=11)),
                ])
            )
        
        products_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Código", size=11, weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Descripción", size=11, weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Cant.", size=11, weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Vr. Unit.", size=11, weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Imp.", size=11, weight=ft.FontWeight.W_600)),
                ft.DataColumn(ft.Text("Total", size=11, weight=ft.FontWeight.W_600)),
            ],
            rows=products_rows,
            border=ft.border.all(1, COLORS["border"]),
            border_radius=8,
            heading_row_color=COLORS["bg_secondary"],
            data_row_min_height=35,
            column_spacing=15,
        )
        
        # Tabs para información
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(
                    text="Productos",
                    content=ft.Container(
                        content=ft.Column([products_table], scroll=ft.ScrollMode.AUTO),
                        padding=10, height=250,
                    ),
                ),
                ft.Tab(
                    text="Cliente",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(f"NIT: {customer.get('identification_number', doc.customer_nit)}", color=COLORS["text_primary"]),
                            ft.Text(f"Nombre: {customer.get('name', doc.customer_name)}", color=COLORS["text_primary"]),
                            ft.Text(f"Email: {customer.get('email', doc.customer_email)}", color=COLORS["text_primary"]),
                            ft.Text(f"Teléfono: {customer.get('phone', 'N/A')}", color=COLORS["text_primary"]),
                            ft.Text(f"Dirección: {customer.get('address', 'N/A')}", color=COLORS["text_primary"]),
                        ], spacing=8),
                        padding=10, height=250,
                    ),
                ),
                ft.Tab(
                    text="Respuesta DIAN",
                    content=ft.Container(
                        content=ft.Column([
                            ft.Text(f"CUFE: {doc.cufe or 'N/A'}", color=COLORS["text_primary"], selectable=True, size=11),
                            ft.Divider(color=COLORS["border"]),
                            ft.Text("Respuesta API:", weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                            ft.TextField(
                                value=json.dumps(api_response, indent=2, ensure_ascii=False) if api_response else "Sin respuesta",
                                multiline=True, read_only=True, min_lines=8, max_lines=12,
                                text_size=10, bgcolor=COLORS["bg_secondary"],
                                border_color=COLORS["border"], color=COLORS["text_primary"],
                            ),
                        ], spacing=8, scroll=ft.ScrollMode.AUTO),
                        padding=10, height=250,
                    ),
                ),
            ],
            indicator_color=COLORS["primary"],
            label_color=COLORS["text_primary"],
            unselected_label_color=COLORS["text_secondary"],
        )
        
        type_labels = {"invoice": "Factura", "credit_note": "Nota Crédito", "debit_note": "Nota Débito"}
        
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.DESCRIPTION, color=COLORS["primary"]),
                ft.Text(f"{type_labels.get(doc.type, 'Documento')} {doc.full_number}", size=18, weight=ft.FontWeight.W_600),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"Cliente: {doc.customer_name}", color=COLORS["text_secondary"], expand=True),
                        status_badge(doc.status),
                    ]),
                    ft.Row([
                        ft.Text(f"Fecha: {doc.issue_date.strftime('%d/%m/%Y %H:%M') if doc.issue_date else 'N/A'}", color=COLORS["text_secondary"]),
                        ft.Text(f"Subtotal: $ {doc.subtotal:,.0f}", color=COLORS["text_secondary"]),
                        ft.Text(f"IVA: $ {doc.total_tax:,.0f}", color=COLORS["text_secondary"]),
                        ft.Text(f"Total: $ {doc.total:,.0f}", color=COLORS["success"], weight=ft.FontWeight.W_600),
                    ], spacing=20),
                    ft.Divider(color=COLORS["border"]),
                    tabs,
                ], spacing=10),
                width=650, height=380,
            ),
            actions=[ft.TextButton("Cerrar", on_click=lambda e: self._close(dlg))],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _print_ticket(self, doc: Document):
        """Generar e imprimir ticket 80mm en PDF con todos los datos reglamentarios DIAN"""
        import os
        from io import BytesIO
        
        try:
            import qrcode
            from reportlab.lib.units import mm as mm_unit
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
        except ImportError:
            snackbar(self.page, "Instale: pip install qrcode reportlab", "danger")
            return
        
        # Obtener configuración de empresa y resolución
        from database import Settings, Municipality, Department
        session = get_session()
        settings = session.query(Settings).first()
        resolution = session.query(Resolution).filter(
            Resolution.type_document_id == doc.type_document_id,
            Resolution.prefix == doc.prefix
        ).first()
        
        # Obtener municipio y departamento del emisor
        municipality = session.query(Municipality).get(settings.municipality_id) if settings and settings.municipality_id else None
        department = session.query(Department).get(settings.department_id) if settings and settings.department_id else None
        
        # Obtener documento de referencia si es NC/ND
        ref_doc = None
        if doc.type in ["credit_note", "debit_note"] and doc.reference_document_id:
            ref_doc = session.query(Document).get(doc.reference_document_id)
        
        session.close()
        
        parsed_data = doc.parsed_data or {}
        lines = parsed_data.get("lines", [])
        customer = parsed_data.get("customer", {})
        
        # Tamaño del ticket: 80mm de ancho
        TICKET_WIDTH = 80 * mm_unit
        LINE_HEIGHT = 3.2 * mm_unit
        SMALL_LINE = 2.8 * mm_unit
        MARGIN = 2 * mm_unit
        
        # Calcular altura estimada del ticket
        num_lines = len(lines)
        estimated_height = (220 + (num_lines * 12)) * mm_unit
        
        # Crear PDF
        downloads_path = os.path.expanduser("~/Downloads")
        pdf_path = os.path.join(downloads_path, f"ticket_{doc.full_number}.pdf")
        
        c = canvas.Canvas(pdf_path, pagesize=(TICKET_WIDTH, estimated_height))
        
        # Usar fuente Courier (monoespaciada, más compacta)
        FONT = "Courier"
        FONT_BOLD = "Courier-Bold"
        
        y = estimated_height - MARGIN * 2
        
        def draw_centered(text, font_name=FONT, font_size=8):
            nonlocal y
            c.setFont(font_name, font_size)
            text_width = c.stringWidth(text, font_name, font_size)
            c.drawString((TICKET_WIDTH - text_width) / 2, y, text)
            y -= LINE_HEIGHT
        
        def draw_left(text, font_name=FONT, font_size=7):
            nonlocal y
            c.setFont(font_name, font_size)
            c.drawString(MARGIN, y, text)
            y -= LINE_HEIGHT
        
        def space(h=1.5):
            nonlocal y
            y -= h * mm_unit
        
        # ========== ENCABEZADO EMISOR ==========
        company_name = (settings.company_name or "EMPRESA").upper()
        company_nit = settings.company_nit or ""
        company_dv = settings.company_dv or ""
        company_address = settings.company_address or ""
        company_phone = settings.company_phone or ""
        company_email = settings.company_email or ""
        
        draw_centered(company_name, FONT_BOLD, 10)
        draw_centered(f"NIT: {company_nit}-{company_dv}", FONT_BOLD, 9)
        regime_text = "RESPONSABLE DE IVA" if settings and settings.type_regime_id == 1 else "NO RESPONSABLE DE IVA"
        draw_centered(regime_text, FONT, 7)
        if company_address:
            draw_centered(company_address[:45], FONT, 7)
        # Municipio y Departamento del emisor
        if municipality and department:
            draw_centered(f"{municipality.name} - {department.name}", FONT, 7)
        if company_phone:
            draw_centered(f"Tel: {company_phone}", FONT, 7)
        if company_email:
            draw_centered(company_email[:42], FONT, 6)
        
        space(2)
        
        # ========== TIPO DE DOCUMENTO ==========
        type_labels = {
            "invoice": "FACTURA ELECTRONICA DE VENTA",
            "credit_note": "NOTA CREDITO ELECTRONICA", 
            "debit_note": "NOTA DEBITO ELECTRONICA"
        }
        draw_centered(type_labels.get(doc.type, "DOCUMENTO"), FONT_BOLD, 9)
        draw_centered(f"No. {doc.full_number}", FONT_BOLD, 10)
        fecha_str = doc.issue_date.strftime('%Y-%m-%d %H:%M') if doc.issue_date else ''
        draw_centered(f"Fecha: {fecha_str}", FONT, 8)
        
        space(2)
        
        # ========== DATOS DEL CLIENTE ==========
        draw_centered("ADQUIRIENTE", FONT_BOLD, 8)
        space(1)
        customer_name = customer.get('name', doc.customer_name) or "CONSUMIDOR FINAL"
        customer_nit = customer.get('identification_number', doc.customer_nit) or ""
        customer_address = customer.get('address', '') or ""
        customer_phone_c = customer.get('phone', '') or ""
        
        draw_left(f"Cliente: {customer_name[:38]}", FONT, 7)
        draw_left(f"NIT/CC: {customer_nit}", FONT, 7)
        if customer_address:
            draw_left(f"Dir: {customer_address[:40]}", FONT, 6)
        if customer_phone_c:
            draw_left(f"Tel: {customer_phone_c}", FONT, 6)
        
        space(2)
        
        # ========== REFERENCIA FACTURA (solo NC/ND) ==========
        if doc.type in ["credit_note", "debit_note"]:
            discrepancy_code = parsed_data.get("discrepancy_code", "")
            discrepancy_desc = parsed_data.get("discrepancy_description", "")
            
            # Motivos NC
            nc_motivos = {
                "1": "Devolucion parcial",
                "2": "Anulacion de factura",
                "3": "Rebaja o descuento",
                "4": "Ajuste de precio",
                "5": "Otros"
            }
            # Motivos ND
            nd_motivos = {
                "1": "Intereses",
                "2": "Gastos por cobrar",
                "3": "Cambio del valor",
                "4": "Otros"
            }
            
            if doc.type == "credit_note":
                motivo = nc_motivos.get(str(discrepancy_code), discrepancy_desc or "N/A")
            else:
                motivo = nd_motivos.get(str(discrepancy_code), discrepancy_desc or "N/A")
            
            draw_centered("DOCUMENTO DE REFERENCIA", FONT_BOLD, 7)
            space(0.5)
            if ref_doc:
                draw_left(f"Factura: {ref_doc.full_number}", FONT, 7)
                if ref_doc.issue_date:
                    draw_left(f"Fecha: {ref_doc.issue_date.strftime('%Y-%m-%d')}", FONT, 7)
                if ref_doc.cufe:
                    draw_left(f"CUFE: {ref_doc.cufe[:40]}...", FONT, 5)
            draw_left(f"Motivo: {motivo[:40]}", FONT, 7)
            if discrepancy_desc and discrepancy_desc != motivo:
                draw_left(f"Desc: {discrepancy_desc[:42]}", FONT, 6)
            
            space(2)
        
        # ========== PRODUCTOS - ENCABEZADO ==========
        c.setFont(FONT_BOLD, 7)
        c.drawString(MARGIN, y, "Cant")
        c.drawString(MARGIN + 8*mm_unit, y, "Descripcion")
        c.drawString(MARGIN + 42*mm_unit, y, "V.Unit")
        c.drawString(MARGIN + 55*mm_unit, y, "Imp")
        c.drawRightString(TICKET_WIDTH - MARGIN, y, "Total")
        y -= LINE_HEIGHT
        space(0.5)
        
        # ========== PRODUCTOS - DETALLE ==========
        for line in lines:
            desc = line.get("description", "Producto")[:22]
            qty = float(line.get("quantity", 1))
            unit_price = float(line.get("unit_price", 0))
            total_line = float(line.get("total", 0))
            tax_id = int(line.get("tax_id", 1))
            tax_pct = float(line.get("tax_percent", 0))
            
            # Determinar etiqueta de impuesto
            if tax_pct == 0:
                tax_label = "Exc"
            elif tax_id == 4:
                tax_label = f"IC{tax_pct:.0f}"
            else:
                tax_label = f"{tax_pct:.0f}%"
            
            c.setFont(FONT, 7)
            c.drawString(MARGIN, y, f"{qty:.0f}")
            c.drawString(MARGIN + 8*mm_unit, y, desc)
            c.drawString(MARGIN + 42*mm_unit, y, f"{unit_price:,.0f}")
            c.drawString(MARGIN + 55*mm_unit, y, tax_label)
            c.drawRightString(TICKET_WIDTH - MARGIN, y, f"{total_line:,.0f}")
            y -= SMALL_LINE
        
        space(2)
        
        # ========== TOTAL REGISTROS Y CANTIDADES ==========
        total_registros = len(lines)
        total_cantidades = sum(float(line.get("quantity", 0)) for line in lines)
        
        c.setFont(FONT, 7)
        c.drawString(MARGIN, y, f"Total Registros: {total_registros:04d}")
        y -= LINE_HEIGHT
        c.drawString(MARGIN, y, f"Total Cantidades: {total_cantidades:.0f}")
        y -= LINE_HEIGHT
        
        space(2)
        
        # ========== RESUMEN DE IMPUESTOS ==========
        # Agrupar por (tax_id, porcentaje)
        # tax_id: 1=IVA, 4=INC (Impuesto al Consumo)
        tax_summary = {}
        for line in lines:
            tax_id = int(line.get("tax_id", 1))
            tax_pct = float(line.get("tax_percent", 0))
            base = float(line.get("total", 0))
            tax_amt = float(line.get("tax_amount", 0))
            if tax_amt == 0 and tax_pct > 0:
                tax_amt = base * (tax_pct / 100)
            
            key = f"{tax_id}_{tax_pct}"
            if key not in tax_summary:
                tax_summary[key] = {"tax_id": tax_id, "percent": tax_pct, "base": 0, "tax": 0}
            tax_summary[key]["base"] += base
            tax_summary[key]["tax"] += tax_amt
        
        if tax_summary:
            draw_centered("RESUMEN IMPUESTOS", FONT_BOLD, 7)
            space(0.5)
            # Encabezado
            c.setFont(FONT_BOLD, 6)
            c.drawString(MARGIN, y, "Tipo")
            c.drawString(MARGIN + 12*mm_unit, y, "Base")
            c.drawString(MARGIN + 35*mm_unit, y, "%")
            c.drawRightString(TICKET_WIDTH - MARGIN, y, "Valor")
            y -= LINE_HEIGHT
            
            # Detalle por cada tipo de impuesto
            for key in sorted(tax_summary.keys()):
                data = tax_summary[key]
                tax_id = data["tax_id"]
                tax_pct = data["percent"]
                
                # Determinar nombre del impuesto
                if tax_pct == 0:
                    tax_name = "Excluido"
                elif tax_id == 4:
                    tax_name = "INC"
                else:
                    tax_name = "IVA"
                
                c.setFont(FONT, 6)
                c.drawString(MARGIN, y, tax_name)
                c.drawString(MARGIN + 12*mm_unit, y, f"{data['base']:,.0f}")
                c.drawString(MARGIN + 35*mm_unit, y, f"{tax_pct:.0f}%")
                c.drawRightString(TICKET_WIDTH - MARGIN, y, f"{data['tax']:,.0f}")
                y -= SMALL_LINE
            
            space(2)
        
        # ========== TOTALES ==========
        subtotal = float(doc.subtotal or 0)
        total_tax = float(doc.total_tax or 0)
        total = float(doc.total or 0)
        
        c.setFont(FONT, 8)
        c.drawString(MARGIN, y, "Subtotal:")
        c.drawRightString(TICKET_WIDTH - MARGIN, y, f"${subtotal:,.0f}")
        y -= LINE_HEIGHT
        
        c.drawString(MARGIN, y, "Impuestos:")
        c.drawRightString(TICKET_WIDTH - MARGIN, y, f"${total_tax:,.0f}")
        y -= LINE_HEIGHT
        
        space(1)
        c.setFont(FONT_BOLD, 10)
        c.drawString(MARGIN, y, "TOTAL:")
        c.drawRightString(TICKET_WIDTH - MARGIN, y, f"${total:,.0f}")
        y -= LINE_HEIGHT * 1.2
        
        # ========== FORMA DE PAGO ==========
        payment_info = parsed_data.get("payment", {})
        payment_name = payment_info.get("payment_name", "Contado")
        payment_form_id = payment_info.get("payment_form_id", 1)
        forma_pago = "Crédito" if payment_form_id == 2 else "Contado"
        
        c.setFont(FONT, 7)
        c.drawString(MARGIN, y, f"Forma de Pago: {forma_pago} - {payment_name}")
        y -= LINE_HEIGHT
        
        space(2)
        
        # ========== RESOLUCIÓN DIAN ==========
        draw_centered("RESOLUCION DIAN", FONT_BOLD, 7)
        
        if resolution:
            draw_centered(f"Resolucion No. {resolution.resolution}", FONT, 6)
            if resolution.resolution_date:
                draw_centered(f"Fecha: {resolution.resolution_date.strftime('%Y-%m-%d')}", FONT, 6)
            if resolution.date_from and resolution.date_to:
                vigencia = f"Vigencia: {resolution.date_from.strftime('%Y-%m-%d')} a {resolution.date_to.strftime('%Y-%m-%d')}"
                draw_centered(vigencia, FONT, 5)
            draw_centered(f"Prefijo: {resolution.prefix} del {resolution.from_number} al {resolution.to_number}", FONT, 6)
        
        space(2)
        
        # ========== CUFE/CUDE ==========
        cufe_label = "CUFE" if doc.type == "invoice" else "CUDE"
        draw_centered(cufe_label, FONT_BOLD, 7)
        
        if doc.cufe:
            cufe = doc.cufe
            chunk_size = 48
            for i in range(0, len(cufe), chunk_size):
                chunk = cufe[i:i+chunk_size]
                draw_centered(chunk, FONT, 5)
            
            space(2)
            
            # URL según ambiente (habilitación o producción)
            is_production = settings and settings.type_environment_id == 1
            if is_production:
                qr_url = f"https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey={doc.cufe}"
                dian_url = "catalogo-vpfe.dian.gov.co"
            else:
                qr_url = f"https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={doc.cufe}"
                dian_url = "catalogo-vpfe-hab.dian.gov.co"
            
            # QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=1)
            qr.add_data(qr_url)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            
            qr_size = 26 * mm_unit
            qr_x = (TICKET_WIDTH - qr_size) / 2
            c.drawImage(ImageReader(qr_buffer), qr_x, y - qr_size, width=qr_size, height=qr_size)
            y -= qr_size + 2 * mm_unit
            
            draw_centered(f"Consulte en: {dian_url}", FONT, 5)
        
        space(2)
        
        # ========== PIE DE PÁGINA ==========
        draw_centered("Representacion grafica de", FONT, 6)
        draw_centered("Factura Electronica", FONT, 6)
        space(1)
        draw_centered("Gracias por su compra!", FONT_BOLD, 8)
        
        space(3)
        
        # ========== EMITIDO POR (DATOS DEL EMISOR) ==========
        draw_centered(f"Emitido por: {company_name}", FONT, 6)
        draw_centered(f"NIT: {company_nit}-{company_dv}", FONT, 6)
        draw_centered("Modalidad: Software propio", FONT, 6)
        
        # Guardar PDF
        try:
            c.save()
        except PermissionError:
            snackbar(self.page, "Cierre el PDF anterior antes de imprimir otro", "warning")
            return
        
        # Enviar directamente a impresión
        try:
            import sys
            if sys.platform == 'win32':
                import ctypes
                result = ctypes.windll.shell32.ShellExecuteW(
                    None, "print", pdf_path, None, None, 1
                )
                if result > 32:
                    snackbar(self.page, "Enviado a impresión", "success")
                else:
                    os.startfile(pdf_path)
                    snackbar(self.page, "Ticket abierto - Use Ctrl+P para imprimir", "success")
            else:
                os.startfile(pdf_path)
                snackbar(self.page, "Ticket abierto - Use Ctrl+P para imprimir", "success")
        except Exception as e:
            snackbar(self.page, f"Ticket guardado: {pdf_path}", "success")

    def _close(self, dlg):
        dlg.open = False
        self.page.update()
