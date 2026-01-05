"""Vista de resoluciones"""
import flet as ft
from datetime import datetime
from database import get_session, Resolution
from services import ApiDianService
from views.theme import COLORS, button, text_field, dropdown, badge, snackbar


class ResolutionsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.list = ft.ListView(expand=True, spacing=1)

    def build(self) -> ft.Container:
        actions = ft.Row([
            button("Nueva Resolución", self._show_create, color="success", icon=ft.Icons.ADD),
            button("Consultar DIAN", self._sync_dian, color="info", icon=ft.Icons.CLOUD_DOWNLOAD),
            button("Actualizar", self._load, icon=ft.Icons.REFRESH),
        ], spacing=10)
        self._load()
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, color=COLORS["primary"], size=28),
                        ft.Text("Resoluciones", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])], spacing=12),
                actions, ft.Divider(color=COLORS["border"]),
                ft.Container(content=self.list, expand=True, bgcolor=COLORS["bg_primary"]),
            ], expand=True, spacing=10),
            expand=True, padding=24, bgcolor=COLORS["bg_primary"],
        )

    def _load(self, e=None):
        session = get_session()
        resolutions = session.query(Resolution).order_by(Resolution.type_document_id).all()
        session.close()
        self.list.controls.clear()
        header = ft.Container(
            content=ft.Row([
                ft.Text("Tipo", width=120, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Prefijo", width=80, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Resolución", width=130, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Rango", width=140, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Actual", width=80, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Vence", width=100, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Estado", width=80, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
                ft.Text("Acciones", width=140, weight=ft.FontWeight.W_600, color=COLORS["text_secondary"], size=12),
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            bgcolor=COLORS["bg_secondary"],
            border_radius=ft.border_radius.only(top_left=8, top_right=8),
        )
        self.list.controls.append(header)
        for r in resolutions:
            self.list.controls.append(self._row(r))
        self.page.update()

    def _row(self, r: Resolution) -> ft.Container:
        type_labels = {1: "Factura", 4: "Nota Crédito", 5: "Nota Débito", 11: "Doc. Soporte", 13: "Nota Ajuste DS"}
        type_colors = {1: "primary", 4: "warning", 5: "info", 11: "success", 13: "danger"}
        vence = r.date_to.strftime("%d/%m/%Y") if r.date_to else "-"
        return ft.Container(
            content=ft.Row([
                ft.Container(content=badge(type_labels.get(r.type_document_id, "Otro"), type_colors.get(r.type_document_id, "primary")), width=120),
                ft.Text(r.prefix or "", width=80, color=COLORS["text_primary"], size=13),
                ft.Text(r.resolution or "", width=130, color=COLORS["text_primary"], size=13),
                ft.Text(f"{r.from_number} - {r.to_number}", width=140, color=COLORS["text_primary"], size=13),
                ft.Text(str(r.current_number), width=80, color=COLORS["text_primary"], size=13),
                ft.Text(vence, width=100, color=COLORS["text_primary"], size=13),
                ft.Container(content=badge("Activa", "success") if r.is_active else badge("Inactiva", "danger"), width=80),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.EDIT, icon_color=COLORS["primary"], tooltip="Editar", icon_size=20, on_click=lambda e, x=r: self._show_edit(x)),
                    ft.IconButton(icon=ft.Icons.SYNC, icon_color=COLORS["success"], tooltip="Sincronizar API", icon_size=20, on_click=lambda e, x=r: self._sync(x)),
                    ft.IconButton(icon=ft.Icons.DELETE, icon_color=COLORS["danger"], tooltip="Eliminar", icon_size=20, on_click=lambda e, x=r: self._delete(x)),
                ], width=140, spacing=0),
            ], spacing=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=10),
            bgcolor=COLORS["bg_card"],
            border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        )

    def _show_create(self, e=None):
        """Mostrar diálogo para crear nueva resolución"""
        type_dd = dropdown("Tipo de Documento", "1", [
            ft.dropdown.Option("1", "Factura de Venta"),
            ft.dropdown.Option("4", "Nota Crédito"),
            ft.dropdown.Option("5", "Nota Débito"),
            ft.dropdown.Option("11", "Documento Soporte"),
            ft.dropdown.Option("13", "Nota Ajuste a Doc. Soporte"),
        ], width=300)
        prefix_tf = text_field("Prefijo", "", width=150)
        resolution_tf = text_field("Número Resolución", "", width=250)
        resolution_date_tf = text_field("Fecha Resolución (YYYY-MM-DD)", "", width=220)
        technical_key_tf = text_field("Clave Técnica", "")
        from_tf = text_field("Desde", "1", width=140)
        to_tf = text_field("Hasta", "5000", width=140)
        current_tf = text_field("Actual", "0", width=140)
        date_from_tf = text_field("Vigencia Desde (YYYY-MM-DD)", "", width=220)
        date_to_tf = text_field("Vigencia Hasta (YYYY-MM-DD)", "", width=220)

        def save(e):
            session = get_session()
            type_labels = {1: "Factura de Venta", 4: "Nota Crédito", 5: "Nota Débito", 11: "Documento Soporte", 13: "Nota Ajuste DS"}
            type_id = int(type_dd.value)
            prefix_value = prefix_tf.value
            res = Resolution(
                type_document_id=type_id,
                type_document_name=type_labels.get(type_id, "Factura"),
                prefix=prefix_value,
                resolution=resolution_tf.value,
                resolution_date=datetime.strptime(resolution_date_tf.value, "%Y-%m-%d") if resolution_date_tf.value else None,
                technical_key=technical_key_tf.value,
                from_number=int(from_tf.value or 1),
                to_number=int(to_tf.value or 5000),
                current_number=int(current_tf.value or 0),
                date_from=datetime.strptime(date_from_tf.value, "%Y-%m-%d") if date_from_tf.value else None,
                date_to=datetime.strptime(date_to_tf.value, "%Y-%m-%d") if date_to_tf.value else None,
                is_active=True,
            )
            session.add(res)
            session.commit()
            session.close()
            dlg.open = False
            self.page.update()
            snackbar(self.page, f"Resolución {prefix_value} creada", "success")
            self._load()

        dlg = ft.AlertDialog(
            title=ft.Text("Nueva Resolución", size=20, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    type_dd,
                    ft.Row([prefix_tf, resolution_tf], spacing=16),
                    resolution_date_tf,
                    technical_key_tf,
                    ft.Row([from_tf, to_tf, current_tf], spacing=16),
                    ft.Row([date_from_tf, date_to_tf], spacing=16),
                ], spacing=16),
                width=500,
                padding=ft.padding.only(top=10),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close(dlg)),
                ft.ElevatedButton(
                    text="Guardar",
                    on_click=save,
                    bgcolor=COLORS["success"],
                    color="#ffffff",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=24, vertical=14),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _show_edit(self, resolution: Resolution):
        """Mostrar diálogo para editar resolución"""
        type_dd = dropdown("Tipo de Documento", str(resolution.type_document_id), [
            ft.dropdown.Option("1", "Factura de Venta"),
            ft.dropdown.Option("4", "Nota Crédito"),
            ft.dropdown.Option("5", "Nota Débito"),
            ft.dropdown.Option("11", "Documento Soporte"),
            ft.dropdown.Option("13", "Nota Ajuste a Doc. Soporte"),
        ], width=300)
        prefix_tf = text_field("Prefijo", resolution.prefix or "", width=150)
        resolution_tf = text_field("Número Resolución", resolution.resolution or "", width=250)
        resolution_date_tf = text_field("Fecha Resolución", resolution.resolution_date.strftime("%Y-%m-%d") if resolution.resolution_date else "", width=220)
        technical_key_tf = text_field("Clave Técnica", resolution.technical_key or "")
        from_tf = text_field("Desde", str(resolution.from_number or 1), width=140)
        to_tf = text_field("Hasta", str(resolution.to_number or 5000), width=140)
        current_tf = text_field("Actual", str(resolution.current_number or 0), width=140)
        date_from_tf = text_field("Vigencia Desde", resolution.date_from.strftime("%Y-%m-%d") if resolution.date_from else "", width=220)
        date_to_tf = text_field("Vigencia Hasta", resolution.date_to.strftime("%Y-%m-%d") if resolution.date_to else "", width=220)
        active_cb = ft.Checkbox(label="Activa", value=resolution.is_active, fill_color=COLORS["primary"])

        def save(e):
            session = get_session()
            res = session.query(Resolution).get(resolution.id)
            type_labels = {1: "Factura de Venta", 4: "Nota Crédito", 5: "Nota Débito", 11: "Documento Soporte", 13: "Nota Ajuste DS"}
            type_id = int(type_dd.value)
            res.type_document_id = type_id
            res.type_document_name = type_labels.get(type_id, "Factura")
            res.prefix = prefix_tf.value
            res.resolution = resolution_tf.value
            res.resolution_date = datetime.strptime(resolution_date_tf.value, "%Y-%m-%d") if resolution_date_tf.value else None
            res.technical_key = technical_key_tf.value
            res.from_number = int(from_tf.value or 1)
            res.to_number = int(to_tf.value or 5000)
            res.current_number = int(current_tf.value or 0)
            res.date_from = datetime.strptime(date_from_tf.value, "%Y-%m-%d") if date_from_tf.value else None
            res.date_to = datetime.strptime(date_to_tf.value, "%Y-%m-%d") if date_to_tf.value else None
            res.is_active = active_cb.value
            prefix_value = res.prefix  # Guardar antes de cerrar sesión
            session.commit()
            session.close()
            dlg.open = False
            self.page.update()
            snackbar(self.page, f"Resolución {prefix_value} actualizada", "success")
            self._load()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Editar Resolución {resolution.prefix}", size=20, weight=ft.FontWeight.W_600),
            content=ft.Container(
                content=ft.Column([
                    type_dd,
                    ft.Row([prefix_tf, resolution_tf], spacing=16),
                    resolution_date_tf,
                    technical_key_tf,
                    ft.Row([from_tf, to_tf, current_tf], spacing=16),
                    ft.Row([date_from_tf, date_to_tf], spacing=16),
                    active_cb,
                ], spacing=16),
                width=500,
                padding=ft.padding.only(top=10),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close(dlg)),
                ft.ElevatedButton(
                    text="Guardar",
                    on_click=save,
                    bgcolor=COLORS["primary"],
                    color="#ffffff",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        padding=ft.padding.symmetric(horizontal=24, vertical=14),
                    ),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _sync(self, resolution: Resolution):
        """Sincronizar resolución con ApiDian"""
        # Guardar valores antes de cualquier operación de sesión
        resolution_id = resolution.id
        prefix_value = resolution.prefix
        
        service = ApiDianService()
        result = service.configure_resolution(resolution)
        if result.get("success"):
            session = get_session()
            res = session.query(Resolution).get(resolution_id)
            res.synced_with_api = True
            session.commit()
            session.close()
            snackbar(self.page, f"Resolución {prefix_value} sincronizada con ApiDian", "success")
            self._load()
        else:
            snackbar(self.page, f"Error: {result.get('message', 'Error desconocido')}", "danger")

    def _sync_dian(self, e=None):
        """Consultar resoluciones desde la DIAN"""
        service = ApiDianService()
        result = service.get_numbering_range()
        
        if not result.get("success"):
            # Verificar si hay mensaje de éxito en la respuesta
            msg = result.get("message", "")
            if "éxito" not in msg.lower():
                snackbar(self.page, f"Error: {msg or 'Error al consultar DIAN'}", "danger")
                return
        
        response_dian = result.get("ResponseDian")
        if not response_dian:
            snackbar(self.page, "No se recibió respuesta de la DIAN", "warning")
            return
        
        # Navegar la estructura de respuesta
        try:
            ranges = response_dian.get("Envelope", {}).get("Body", {}).get("GetNumberingRangeResponse", {}).get("GetNumberingRangeResult", {}).get("ResponseList", {}).get("NumberRangeResponse", [])
        except:
            ranges = []
        
        if not ranges:
            snackbar(self.page, "No se encontraron resoluciones en la DIAN", "info")
            return
        
        # Si solo hay una resolución, convertir a lista
        if isinstance(ranges, dict):
            ranges = [ranges]
        
        session = get_session()
        created = 0
        updated = 0
        
        for r in ranges:
            prefix = r.get("Prefix", "")
            resolution_number = r.get("ResolutionNumber", "")
            resolution_date = r.get("ResolutionDate")
            technical_key = r.get("TechnicalKey", "")
            from_num = int(r.get("FromNumber", 1))
            to_num = int(r.get("ToNumber", 5000))
            valid_from = r.get("ValidDateFrom")
            valid_to = r.get("ValidDateTo")
            
            # Determinar tipo de documento por prefijo
            type_id = self._guess_document_type(prefix)
            type_labels = {1: "Factura de Venta", 4: "Nota Crédito", 5: "Nota Débito", 11: "Documento Soporte", 13: "Nota Ajuste DS"}
            
            # Buscar si ya existe
            existing = session.query(Resolution).filter(
                Resolution.resolution == resolution_number,
                Resolution.prefix == prefix
            ).first()
            
            if existing:
                existing.resolution_date = datetime.strptime(resolution_date, "%Y-%m-%d") if resolution_date else None
                existing.technical_key = technical_key
                existing.to_number = to_num
                existing.date_from = datetime.strptime(valid_from, "%Y-%m-%d") if valid_from else None
                existing.date_to = datetime.strptime(valid_to, "%Y-%m-%d") if valid_to else None
                updated += 1
            else:
                new_res = Resolution(
                    type_document_id=type_id,
                    type_document_name=type_labels.get(type_id, "Factura"),
                    prefix=prefix,
                    resolution=resolution_number,
                    resolution_date=datetime.strptime(resolution_date, "%Y-%m-%d") if resolution_date else None,
                    technical_key=technical_key,
                    from_number=from_num,
                    to_number=to_num,
                    current_number=from_num - 1,
                    date_from=datetime.strptime(valid_from, "%Y-%m-%d") if valid_from else None,
                    date_to=datetime.strptime(valid_to, "%Y-%m-%d") if valid_to else None,
                    is_active=False,
                )
                session.add(new_res)
                created += 1
        
        session.commit()
        session.close()
        snackbar(self.page, f"Sincronización: {created} creadas, {updated} actualizadas", "success")
        self._load()

    def _guess_document_type(self, prefix: str) -> int:
        """Determinar tipo de documento por prefijo"""
        prefix = prefix.upper()
        if "NC" in prefix or "CRED" in prefix:
            return 4
        if "ND" in prefix or "DEB" in prefix:
            return 5
        if "DS" in prefix or "SOPORTE" in prefix:
            return 11
        if "NDS" in prefix or "ADS" in prefix or "NADS" in prefix:
            return 13
        return 1

    def _delete(self, resolution: Resolution):
        """Eliminar resolución"""
        # Guardar valores antes de cualquier operación de sesión
        resolution_id = resolution.id
        prefix_value = resolution.prefix
        resolution_number = resolution.resolution
        
        def confirm(e):
            session = get_session()
            res = session.query(Resolution).get(resolution_id)
            session.delete(res)
            session.commit()
            session.close()
            dlg.open = False
            self.page.update()
            snackbar(self.page, f"Resolución {prefix_value} eliminada", "success")
            self._load()

        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar Eliminación", size=18, weight=ft.FontWeight.W_600),
            content=ft.Text(f"¿Está seguro de eliminar la resolución {prefix_value} - {resolution_number}?", color=COLORS["text_secondary"]),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close(dlg)),
                ft.ElevatedButton(
                    text="Eliminar",
                    on_click=confirm,
                    bgcolor=COLORS["danger"],
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

    def _close(self, dlg):
        """Cerrar diálogo"""
        dlg.open = False
        self.page.update()
