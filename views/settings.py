"""Vista de configuración"""
import flet as ft
import os
import base64
from database import (
    get_session, Settings,
    TypeDocumentIdentification, TypeOrganization, TypeRegime,
    TypeLiability, Department, Municipality
)
from services import ApiDianService
from views.theme import COLORS, button, text_field, dropdown, section_title, divider, snackbar


class SettingsView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.settings = None
        self.catalogs = {}
        self._load_data()
        self.fields = {}
        self.certificate_file = None
        self.certificate_filename = None
        self.certificate_content = None

    def _close(self, dlg):
        """Cerrar diálogo"""
        dlg.open = False
        self.page.update()

    def _load_data(self):
        session = get_session()
        self.settings = session.query(Settings).first()
        if not self.settings:
            self.settings = Settings()
            session.add(self.settings)
            session.commit()
        self.catalogs["type_documents"] = {t.id: t.name for t in session.query(TypeDocumentIdentification).all()}
        self.catalogs["type_organizations"] = {t.id: t.name for t in session.query(TypeOrganization).all()}
        self.catalogs["type_regimes"] = {t.id: t.name for t in session.query(TypeRegime).all()}
        self.catalogs["type_liabilities"] = {t.id: t.name for t in session.query(TypeLiability).all()}
        self.catalogs["departments"] = {d.id: d.name for d in session.query(Department).order_by(Department.name).all()}
        self.catalogs["municipalities"] = session.query(Municipality).all()
        session.close()

    def build(self) -> ft.Container:
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Empresa", icon=ft.Icons.BUSINESS, content=self._build_company_tab()),
                ft.Tab(text="API DIAN", icon=ft.Icons.CLOUD, content=self._build_api_tab()),
                ft.Tab(text="Ambiente", icon=ft.Icons.SWAP_HORIZ, content=self._build_environment_tab()),
                ft.Tab(text="Certificado", icon=ft.Icons.VERIFIED_USER, content=self._build_certificate_tab()),
                ft.Tab(text="Correo SMTP", icon=ft.Icons.EMAIL, content=self._build_mail_tab()),
                ft.Tab(text="Carpetas", icon=ft.Icons.FOLDER, content=self._build_folders_tab()),
                ft.Tab(text="Base de Datos", icon=ft.Icons.STORAGE, content=self._build_database_tab()),
            ],
            expand=True,
            indicator_color=COLORS["primary"],
            label_color=COLORS["text_primary"],
            unselected_label_color=COLORS["text_secondary"],
        )
        actions = ft.Row([
            button("Guardar", self._save, color="success", icon=ft.Icons.SAVE),
            button("Probar Conexión", self._test_connection, color="info", icon=ft.Icons.WIFI),
            button("Config Empresa", self._configure_company, icon=ft.Icons.BUSINESS),
            button("Config Software", self._configure_software, color="warning", icon=ft.Icons.SETTINGS),
            button("Config Software DS", self._configure_software_ds, color="primary", icon=ft.Icons.SHOPPING_CART),
        ], spacing=10, wrap=True)
        return ft.Container(
            content=ft.Column([
                ft.Row([ft.Icon(ft.Icons.SETTINGS, color=COLORS["primary"], size=28),
                        ft.Text("Configuración", size=24, weight=ft.FontWeight.BOLD, color=COLORS["text_primary"])], spacing=12),
                actions, divider(), tabs,
            ], expand=True, spacing=10),
            expand=True, padding=24, bgcolor=COLORS["bg_primary"],
        )

    def _build_company_tab(self) -> ft.Container:
        self.fields["type_document_identification_id"] = dropdown("Tipo Documento", str(self.settings.type_document_identification_id or 3),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_documents"].items()], width=280)
        self.fields["company_nit"] = text_field("Número de Documento", self.settings.company_nit or "", width=200)
        self.fields["company_dv"] = text_field("DV", self.settings.company_dv or "", width=70)
        self.fields["company_name"] = text_field("Razón Social / Nombre", self.settings.company_name or "")
        self.fields["merchant_registration"] = text_field("Matrícula Mercantil", self.settings.merchant_registration or "0000000-00", width=180)
        self.fields["type_organization_id"] = dropdown("Tipo Organización", str(self.settings.type_organization_id or 2),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_organizations"].items()], width=320)
        self.fields["type_regime_id"] = dropdown("Tipo Régimen", str(self.settings.type_regime_id or 2),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_regimes"].items()], width=250)
        self.fields["type_liability_id"] = dropdown("Responsabilidad Tributaria", str(self.settings.type_liability_id or 117),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["type_liabilities"].items()], width=320)
        self.fields["department_id"] = dropdown("Departamento", str(self.settings.department_id or 22),
            [ft.dropdown.Option(str(k), v) for k, v in self.catalogs["departments"].items()], width=250, on_change=self._on_department_change)
        dept_id = self.settings.department_id or 22
        muni_options = [ft.dropdown.Option(str(m.id), m.name) for m in self.catalogs["municipalities"] if m.department_id == dept_id]
        self.fields["municipality_id"] = dropdown("Municipio", str(self.settings.municipality_id or 520),
            muni_options if muni_options else [ft.dropdown.Option("520", "Pasto")], width=250)
        self.fields["company_address"] = text_field("Dirección", self.settings.company_address or "")
        self.fields["company_phone"] = text_field("Teléfono", self.settings.company_phone or "", width=180)
        self.fields["company_email"] = text_field("Email", self.settings.company_email or "", width=300)
        return ft.Container(
            content=ft.Column([
                section_title("Datos de la Empresa", "Información registrada ante la DIAN"), divider(),
                ft.Row([self.fields["type_document_identification_id"], self.fields["company_nit"], self.fields["company_dv"]], spacing=12, wrap=True),
                self.fields["company_name"],
                ft.Row([self.fields["merchant_registration"], self.fields["type_organization_id"]], spacing=12, wrap=True),
                ft.Row([self.fields["type_regime_id"], self.fields["type_liability_id"]], spacing=12, wrap=True),
                ft.Row([self.fields["department_id"], self.fields["municipality_id"]], spacing=12, wrap=True),
                self.fields["company_address"],
                ft.Row([self.fields["company_phone"], self.fields["company_email"]], spacing=12, wrap=True),
            ], spacing=16, scroll=ft.ScrollMode.AUTO),
            padding=24, expand=True,
        )

    def _on_department_change(self, e):
        dept_id = int(e.control.value) if e.control.value else 0
        filtered = [(m.id, m.name) for m in self.catalogs["municipalities"] if m.department_id == dept_id]
        self.fields["municipality_id"].options = [ft.dropdown.Option(str(k), name) for k, name in filtered]
        if filtered:
            self.fields["municipality_id"].value = str(filtered[0][0])
        self.page.update()

    def _build_api_tab(self) -> ft.Container:
        self.fields["api_url"] = text_field("URL API", self.settings.api_url or "https://apidian.clipers.pro/api/ubl2.1")
        self.fields["api_token"] = text_field("Token API", self.settings.api_token or "", password=True)
        self.fields["software_id"] = text_field("Software ID", self.settings.software_id or "", width=400)
        self.fields["software_pin"] = text_field("Software PIN", self.settings.software_pin or "", width=150)
        self.fields["test_set_id"] = text_field("Test Set ID", self.settings.test_set_id or "", width=400)
        self.fields["type_environment_id"] = dropdown("Ambiente", str(self.settings.type_environment_id or 2),
            [ft.dropdown.Option("1", "Producción"), ft.dropdown.Option("2", "Habilitación (Pruebas)")], width=280)
        
        # Campos para Documento Soporte
        self.fields["ds_software_id"] = text_field("Software ID (DS)", getattr(self.settings, 'ds_software_id', '') or "", width=400)
        self.fields["ds_software_pin"] = text_field("Software PIN (DS)", getattr(self.settings, 'ds_software_pin', '') or "", width=150)
        self.fields["ds_test_set_id"] = text_field("Test Set ID (DS)", getattr(self.settings, 'ds_test_set_id', '') or "", width=400)
        
        return ft.Container(
            content=ft.Column([
                section_title("Configuración API DIAN", "Datos de conexión con ApiDian"), divider(),
                self.fields["api_url"], self.fields["api_token"],
                ft.Row([self.fields["software_id"], self.fields["software_pin"]], spacing=12, wrap=True),
                ft.Row([self.fields["test_set_id"], self.fields["type_environment_id"]], spacing=12, wrap=True),
                ft.Container(height=16),
                section_title("Documento Soporte Electrónico", "Configuración para compras a no obligados a facturar"), divider(),
                ft.Row([self.fields["ds_software_id"], self.fields["ds_software_pin"]], spacing=12, wrap=True),
                self.fields["ds_test_set_id"],
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=COLORS["info"], size=16),
                        ft.Text(
                            "El Documento Soporte requiere un software_id y pin separados registrados en la DIAN.",
                            color=COLORS["text_secondary"], size=12,
                        ),
                    ], spacing=8),
                    bgcolor=COLORS["bg_secondary"],
                    padding=10,
                    border_radius=8,
                ),
            ], spacing=16, scroll=ft.ScrollMode.AUTO),
            padding=24, expand=True,
        )

    def _build_environment_tab(self) -> ft.Container:
        """Construir pestaña de cambio de ambiente (Habilitación/Producción)"""
        is_production = self.settings.type_environment_id == 1
        
        # Estado actual
        current_env = "Producción" if is_production else "Habilitación (Pruebas)"
        env_color = COLORS["success"] if is_production else COLORS["warning"]
        env_icon = ft.Icons.VERIFIED if is_production else ft.Icons.SCIENCE
        
        self.env_status = ft.Container(
            content=ft.Row([
                ft.Icon(env_icon, color=env_color, size=32),
                ft.Column([
                    ft.Text("Ambiente Actual", color=COLORS["text_secondary"], size=12),
                    ft.Text(current_env, color=env_color, size=20, weight=ft.FontWeight.BOLD),
                ], spacing=2),
            ], spacing=16),
            bgcolor=COLORS["bg_secondary"],
            padding=20,
            border_radius=12,
            border=ft.border.all(2, env_color),
        )
        
        # Selector de ambiente
        self.env_selector = dropdown("Cambiar a", str(self.settings.type_environment_id or 2), [
            ft.dropdown.Option("2", "🧪 Habilitación (Pruebas)"),
            ft.dropdown.Option("1", "✅ Producción"),
        ], width=350)
        
        # Información de cada ambiente
        hab_info = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.SCIENCE, color=COLORS["warning"], size=24),
                    ft.Text("Ambiente de Habilitación", weight=ft.FontWeight.W_600, color=COLORS["warning"]),
                ], spacing=10),
                ft.Text("• URL DIAN: vpfe-hab.dian.gov.co", color=COLORS["text_secondary"], size=12),
                ft.Text("• URL QR: catalogo-vpfe-hab.dian.gov.co", color=COLORS["text_secondary"], size=12),
                ft.Text("• Requiere Test Set ID para enviar documentos", color=COLORS["text_secondary"], size=12),
                ft.Text("• Los documentos NO tienen validez fiscal", color=COLORS["text_secondary"], size=12),
            ], spacing=4),
            bgcolor=COLORS["bg_hover"],
            padding=16,
            border_radius=8,
        )
        
        prod_info = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.VERIFIED, color=COLORS["success"], size=24),
                    ft.Text("Ambiente de Producción", weight=ft.FontWeight.W_600, color=COLORS["success"]),
                ], spacing=10),
                ft.Text("• URL DIAN: vpfe.dian.gov.co", color=COLORS["text_secondary"], size=12),
                ft.Text("• URL QR: catalogo-vpfe.dian.gov.co", color=COLORS["text_secondary"], size=12),
                ft.Text("• NO requiere Test Set ID", color=COLORS["text_secondary"], size=12),
                ft.Text("• Los documentos tienen VALIDEZ FISCAL", color=COLORS["text_secondary"], size=12),
            ], spacing=4),
            bgcolor=COLORS["bg_hover"],
            padding=16,
            border_radius=8,
        )
        
        # Advertencia
        warning_box = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER, color=COLORS["danger"], size=24),
                ft.Column([
                    ft.Text("⚠️ IMPORTANTE", weight=ft.FontWeight.BOLD, color=COLORS["danger"]),
                    ft.Text(
                        "Antes de cambiar a Producción, asegúrese de:\n"
                        "• Haber completado las pruebas de habilitación en la DIAN\n"
                        "• Tener la resolución de facturación configurada con la clave técnica de producción\n"
                        "• Tener el certificado digital vigente",
                        color=COLORS["text_secondary"],
                        size=12,
                    ),
                ], spacing=4, expand=True),
            ], spacing=12),
            bgcolor=COLORS["bg_card"],
            padding=16,
            border_radius=8,
            border=ft.border.all(1, COLORS["danger"]),
        )
        
        return ft.Container(
            content=ft.Column([
                section_title("Cambio de Ambiente", "Migrar entre Habilitación y Producción"),
                divider(),
                self.env_status,
                ft.Container(height=16),
                ft.Row([hab_info, prod_info], spacing=16, wrap=True),
                ft.Container(height=16),
                warning_box,
                ft.Container(height=16),
                ft.Row([
                    self.env_selector,
                    button("Cambiar Ambiente", self._change_environment, color="warning", icon=ft.Icons.SWAP_HORIZ),
                ], spacing=16),
                ft.Container(height=8),
                ft.Text(
                    "📄 Consulte el archivo PRODUCCION.md para ver la guía completa de migración",
                    color=COLORS["info"],
                    size=12,
                    italic=True,
                ),
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=24, expand=True,
        )

    def _change_environment(self, e):
        """Cambiar ambiente de facturación"""
        new_env = int(self.env_selector.value or 2)
        current_env = self.settings.type_environment_id or 2
        
        if new_env == current_env:
            snackbar(self.page, "Ya está en ese ambiente", "info")
            return
        
        env_name = "Producción" if new_env == 1 else "Habilitación"
        
        # Confirmar cambio
        def confirm_change(e):
            dlg.open = False
            self.page.update()
            self._execute_environment_change(new_env)
        
        def cancel_change(e):
            dlg.open = False
            self.page.update()
        
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.WARNING_AMBER, color=COLORS["warning"]),
                ft.Text(f"Cambiar a {env_name}", size=18, weight=ft.FontWeight.W_600),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        f"¿Está seguro de cambiar al ambiente de {env_name}?",
                        color=COLORS["text_primary"],
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Este cambio afectará:\n"
                        "• La URL del servicio web de la DIAN\n"
                        "• La URL del código QR en los documentos\n"
                        "• La validez fiscal de los documentos",
                        color=COLORS["text_secondary"],
                        size=12,
                    ),
                ], spacing=8),
                width=400,
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_change),
                ft.ElevatedButton(
                    f"Cambiar a {env_name}",
                    on_click=confirm_change,
                    bgcolor=COLORS["warning"],
                    color="white",
                ),
            ],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _execute_environment_change(self, new_env: int):
        """Ejecutar el cambio de ambiente"""
        service = ApiDianService()
        result = service.configure_environment(new_env)
        
        if result.get("success"):
            # Actualizar UI
            env_name = "Producción" if new_env == 1 else "Habilitación (Pruebas)"
            env_color = COLORS["success"] if new_env == 1 else COLORS["warning"]
            env_icon = ft.Icons.VERIFIED if new_env == 1 else ft.Icons.SCIENCE
            
            self.env_status.content = ft.Row([
                ft.Icon(env_icon, color=env_color, size=32),
                ft.Column([
                    ft.Text("Ambiente Actual", color=COLORS["text_secondary"], size=12),
                    ft.Text(env_name, color=env_color, size=20, weight=ft.FontWeight.BOLD),
                ], spacing=2),
            ], spacing=16)
            self.env_status.border = ft.border.all(2, env_color)
            
            # Actualizar dropdown en API tab
            self.fields["type_environment_id"].value = str(new_env)
            
            # Limpiar test_set_id si es producción
            if new_env == 1:
                self.fields["test_set_id"].value = ""
            
            # Recargar settings
            self._load_data()
            
            self.page.update()
            snackbar(self.page, f"Ambiente cambiado a {env_name}", "success")
        else:
            snackbar(self.page, f"Error: {result.get('message', 'Error desconocido')}", "danger")

    def _build_mail_tab(self) -> ft.Container:
        self.fields["mail_host"] = text_field("Host SMTP", self.settings.mail_host or "smtp.gmail.com", width=300)
        self.fields["mail_port"] = text_field("Puerto", str(self.settings.mail_port or 587), width=100)
        self.fields["mail_username"] = text_field("Usuario/Email", self.settings.mail_username or "")
        self.fields["mail_password"] = text_field("Contraseña", self.settings.mail_password or "", password=True)
        self.fields["mail_encryption"] = dropdown("Encriptación", self.settings.mail_encryption or "tls",
            [ft.dropdown.Option("tls", "TLS"), ft.dropdown.Option("ssl", "SSL"), ft.dropdown.Option("", "Ninguna")], width=150)
        return ft.Container(
            content=ft.Column([
                section_title("Configuración de Correo SMTP", "Para enviar documentos por email"), divider(),
                ft.Row([self.fields["mail_host"], self.fields["mail_port"]], spacing=12, wrap=True),
                self.fields["mail_username"],
                ft.Row([self.fields["mail_password"], self.fields["mail_encryption"]], spacing=12, wrap=True),
            ], spacing=16),
            padding=24,
        )

    def _build_folders_tab(self) -> ft.Container:
        self.fields["watch_folder"] = text_field("Carpeta de XMLs", self.settings.watch_folder or r"D:\SIIWI01\DOCELECTRONICOS")
        self.fields["processed_folder"] = text_field("Carpeta Procesados", self.settings.processed_folder or r"D:\SIIWI01\DOCELECTRONICOS\procesados")
        
        # File pickers para carpetas
        self.folder_picker_watch = ft.FilePicker(on_result=self._on_watch_folder_selected)
        self.folder_picker_processed = ft.FilePicker(on_result=self._on_processed_folder_selected)
        self.page.overlay.append(self.folder_picker_watch)
        self.page.overlay.append(self.folder_picker_processed)
        
        return ft.Container(
            content=ft.Column([
                section_title("Carpetas de Monitoreo", "Rutas donde Siigo genera los XMLs"), divider(),
                ft.Text("Carpeta de XMLs de Siigo", color=COLORS["text_secondary"], size=13),
                ft.Row([
                    self.fields["watch_folder"],
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        icon_color=COLORS["primary"],
                        tooltip="Seleccionar carpeta",
                        on_click=lambda e: self.folder_picker_watch.get_directory_path(dialog_title="Seleccionar carpeta de XMLs"),
                    ),
                ], spacing=8),
                ft.Container(height=8),
                ft.Text("Carpeta de Procesados", color=COLORS["text_secondary"], size=13),
                ft.Row([
                    self.fields["processed_folder"],
                    ft.IconButton(
                        icon=ft.Icons.FOLDER_OPEN,
                        icon_color=COLORS["primary"],
                        tooltip="Seleccionar carpeta",
                        on_click=lambda e: self.folder_picker_processed.get_directory_path(dialog_title="Seleccionar carpeta de procesados"),
                    ),
                ], spacing=8),
                ft.Container(height=16),
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=COLORS["text_secondary"], size=16),
                        ft.Text(
                            "La carpeta de XMLs es donde Siigo genera los documentos electrónicos.\nLa carpeta de procesados es donde se mueven los XMLs después de enviarlos.",
                            color=COLORS["text_secondary"],
                            size=12,
                        ),
                    ], spacing=8),
                    bgcolor=COLORS["bg_secondary"],
                    padding=12,
                    border_radius=8,
                ),
            ], spacing=8),
            padding=24,
        )

    def _on_watch_folder_selected(self, e: ft.FilePickerResultEvent):
        """Manejar selección de carpeta de XMLs"""
        if e.path:
            self.fields["watch_folder"].value = e.path
            self.page.update()
            snackbar(self.page, f"Carpeta seleccionada: {e.path}", "success")

    def _on_processed_folder_selected(self, e: ft.FilePickerResultEvent):
        """Manejar selección de carpeta de procesados"""
        if e.path:
            self.fields["processed_folder"].value = e.path
            self.page.update()
            snackbar(self.page, f"Carpeta seleccionada: {e.path}", "success")

    def _build_database_tab(self) -> ft.Container:
        """Construir pestaña de configuración de base de datos"""
        from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        
        # Detectar si es servidor o cliente
        is_server = DB_HOST in ["localhost", "127.0.0.1", ""]
        
        self.fields["db_mode"] = dropdown("Modo de Operación", "server" if is_server else "client", [
            ft.dropdown.Option("server", "🖥️ Este es el SERVIDOR (tiene MySQL instalado)"),
            ft.dropdown.Option("client", "💻 Este es un CLIENTE (se conecta al servidor)"),
        ], width=450, on_change=self._on_db_mode_change)
        
        self.fields["db_host"] = text_field("IP del Servidor MySQL", DB_HOST or "localhost", width=250)
        self.fields["db_port"] = text_field("Puerto", DB_PORT or "3306", width=100)
        self.fields["db_name"] = text_field("Base de Datos", DB_NAME or "siigo_python", width=200)
        self.fields["db_user"] = text_field("Usuario", DB_USER or "root", width=180)
        self.fields["db_password"] = text_field("Contraseña", DB_PASSWORD or "", password=True, width=200)
        
        # Campos para configurar servidor
        self.fields["server_ip"] = text_field("IP de este servidor (para clientes)", self._get_local_ip(), width=200)
        self.fields["new_user"] = text_field("Usuario para red", "siigo_net", width=150)
        self.fields["new_password"] = text_field("Contraseña para red", "siigo2024", width=180)
        
        # Estado de conexión
        self.db_status = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.HELP_OUTLINE, color=COLORS["text_secondary"], size=16),
                ft.Text("Sin verificar", color=COLORS["text_secondary"], size=12),
            ], spacing=8),
            bgcolor=COLORS["bg_secondary"],
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            border_radius=8,
        )
        
        # Panel de servidor
        self.server_panel = ft.Container(
            content=ft.Column([
                section_title("Configuración de Servidor", "Configure este equipo como servidor de base de datos"),
                ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.Icons.COMPUTER, color=COLORS["info"], size=20),
                            ft.Text(f"IP de este equipo: {self._get_local_ip()}", color=COLORS["text_primary"], size=14, weight=ft.FontWeight.W_600),
                        ], spacing=10),
                        ft.Text("Los clientes deben usar esta IP para conectarse", color=COLORS["text_secondary"], size=12),
                    ], spacing=4),
                    bgcolor=COLORS["bg_hover"],
                    padding=12,
                    border_radius=8,
                ),
                ft.Container(height=8),
                ft.Text("Crear usuario para acceso en red:", color=COLORS["text_secondary"], size=13),
                ft.Row([self.fields["new_user"], self.fields["new_password"]], spacing=12),
                ft.Container(height=8),
                ft.Row([
                    button("Configurar Servidor", self._setup_server, color="success", icon=ft.Icons.SETTINGS),
                    button("Abrir Firewall", self._open_firewall, color="warning", icon=ft.Icons.SECURITY),
                ], spacing=12),
            ], spacing=10),
            visible=is_server,
            padding=16,
            bgcolor=COLORS["bg_secondary"],
            border_radius=8,
        )
        
        # Panel de cliente
        self.client_panel = ft.Container(
            content=ft.Column([
                section_title("Configuración de Cliente", "Conectar a un servidor MySQL en la red"),
                ft.Text("Ingrese los datos del servidor:", color=COLORS["text_secondary"], size=13),
                ft.Row([self.fields["db_host"], self.fields["db_port"]], spacing=12),
                ft.Row([self.fields["db_user"], self.fields["db_password"]], spacing=12),
                ft.Container(height=8),
                ft.Row([
                    button("Probar Conexión", self._test_db_connection, color="info", icon=ft.Icons.WIFI_FIND),
                    button("Guardar Conexión", self._save_db_config, color="success", icon=ft.Icons.SAVE),
                    self.db_status,
                ], spacing=12),
            ], spacing=10),
            visible=not is_server,
            padding=16,
            bgcolor=COLORS["bg_secondary"],
            border_radius=8,
        )
        
        return ft.Container(
            content=ft.Column([
                section_title("Conexión a Base de Datos", "Configuración para red local con múltiples cajas"), divider(),
                self.fields["db_mode"],
                ft.Container(height=8),
                self.server_panel,
                self.client_panel,
            ], spacing=12, scroll=ft.ScrollMode.AUTO),
            padding=24, expand=True,
        )

    def _get_local_ip(self) -> str:
        """Obtener IP local del equipo"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "192.168.1.X"

    def _on_db_mode_change(self, e):
        """Cambiar entre modo servidor y cliente"""
        is_server = e.control.value == "server"
        self.server_panel.visible = is_server
        self.client_panel.visible = not is_server
        
        if is_server:
            self.fields["db_host"].value = "localhost"
        
        self.page.update()

    def _setup_server(self, e):
        """Configurar MySQL para aceptar conexiones remotas"""
        new_user = self.fields["new_user"].value or "siigo_net"
        new_pass = self.fields["new_password"].value or "siigo2024"
        db_name = self.fields["db_name"].value or "siigo_python"
        
        try:
            from sqlalchemy import create_engine, text
            
            # Conectar como root local
            root_url = f"mysql+pymysql://root:@localhost:3306/"
            engine = create_engine(root_url)
            
            with engine.connect() as conn:
                # Crear base de datos si no existe
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                
                # Eliminar usuario si existe y recrear
                try:
                    conn.execute(text(f"DROP USER IF EXISTS '{new_user}'@'%'"))
                except:
                    pass
                
                # Crear usuario con acceso desde cualquier IP
                conn.execute(text(f"CREATE USER '{new_user}'@'%' IDENTIFIED BY '{new_pass}'"))
                
                # Dar todos los permisos sobre la base de datos
                conn.execute(text(f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{new_user}'@'%'"))
                
                # Aplicar cambios
                conn.execute(text("FLUSH PRIVILEGES"))
                conn.commit()
            
            local_ip = self._get_local_ip()
            
            # Mostrar información para los clientes
            dlg = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["success"]),
                    ft.Text("Servidor Configurado", size=18, weight=ft.FontWeight.W_600),
                ], spacing=10),
                content=ft.Container(
                    content=ft.Column([
                        ft.Text("El servidor está listo para recibir conexiones.", color=COLORS["text_primary"]),
                        ft.Divider(color=COLORS["border"]),
                        ft.Text("Datos para configurar los CLIENTES:", weight=ft.FontWeight.W_600, color=COLORS["info"]),
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"IP del Servidor: {local_ip}", color=COLORS["text_primary"], selectable=True),
                                ft.Text(f"Puerto: 3306", color=COLORS["text_primary"]),
                                ft.Text(f"Usuario: {new_user}", color=COLORS["text_primary"], selectable=True),
                                ft.Text(f"Contraseña: {new_pass}", color=COLORS["text_primary"], selectable=True),
                                ft.Text(f"Base de datos: {db_name}", color=COLORS["text_primary"]),
                            ], spacing=4),
                            bgcolor=COLORS["bg_hover"],
                            padding=12,
                            border_radius=8,
                        ),
                        ft.Container(height=8),
                        ft.Text("⚠️ Recuerde abrir el puerto 3306 en el firewall", color=COLORS["warning"], size=12),
                    ], spacing=8),
                    width=400,
                ),
                actions=[ft.TextButton("Cerrar", on_click=lambda e: self._close(dlg))],
                bgcolor=COLORS["bg_card"],
            )
            self.page.overlay.append(dlg)
            dlg.open = True
            self.page.update()
            
            snackbar(self.page, f"Servidor configurado. Usuario: {new_user}", "success")
            
        except Exception as ex:
            error_msg = str(ex)
            if "Access denied" in error_msg:
                snackbar(self.page, "Error: Necesita acceso root a MySQL. Verifique que MySQL esté instalado.", "danger")
            else:
                snackbar(self.page, f"Error: {error_msg[:100]}", "danger")

    def _open_firewall(self, e):
        """Abrir puerto 3306 en el firewall de Windows"""
        import subprocess
        import sys
        
        try:
            # Primero intentar directamente
            cmd = 'netsh advfirewall firewall add rule name="MySQL SiigoDIAN" dir=in action=allow protocol=tcp localport=3306'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                snackbar(self.page, "Puerto 3306 abierto en el firewall", "success")
                return
            
            # Si falla, intentar con elevación usando PowerShell
            ps_cmd = f'''
            Start-Process -FilePath "netsh" -ArgumentList "advfirewall firewall add rule name=`"MySQL SiigoDIAN`" dir=in action=allow protocol=tcp localport=3306" -Verb RunAs -Wait
            '''
            result2 = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
            
            if result2.returncode == 0:
                snackbar(self.page, "Puerto 3306 abierto en el firewall (con permisos de administrador)", "success")
            else:
                # Mostrar diálogo con instrucciones manuales
                self._show_firewall_instructions()
                
        except Exception as ex:
            self._show_firewall_instructions()

    def _show_firewall_instructions(self):
        """Mostrar instrucciones para abrir el firewall manualmente"""
        dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.SECURITY, color=COLORS["warning"]),
                ft.Text("Abrir Puerto en Firewall", size=18, weight=ft.FontWeight.W_600),
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Para permitir conexiones de red, abra el puerto 3306:", color=COLORS["text_primary"]),
                    ft.Divider(color=COLORS["border"]),
                    ft.Text("Opción 1: Ejecutar como Administrador", weight=ft.FontWeight.W_600, color=COLORS["info"]),
                    ft.Text("Cierre la app, clic derecho → Ejecutar como administrador", color=COLORS["text_secondary"], size=12),
                    ft.Container(height=8),
                    ft.Text("Opción 2: Abrir manualmente", weight=ft.FontWeight.W_600, color=COLORS["info"]),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("1. Buscar 'Firewall de Windows' en el menú inicio", size=11, color=COLORS["text_secondary"]),
                            ft.Text("2. Clic en 'Configuración avanzada'", size=11, color=COLORS["text_secondary"]),
                            ft.Text("3. Reglas de entrada → Nueva regla", size=11, color=COLORS["text_secondary"]),
                            ft.Text("4. Puerto → Siguiente", size=11, color=COLORS["text_secondary"]),
                            ft.Text("5. TCP → Puertos locales: 3306 → Siguiente", size=11, color=COLORS["text_secondary"]),
                            ft.Text("6. Permitir conexión → Siguiente → Siguiente", size=11, color=COLORS["text_secondary"]),
                            ft.Text("7. Nombre: 'MySQL' → Finalizar", size=11, color=COLORS["text_secondary"]),
                        ], spacing=2),
                        bgcolor=COLORS["bg_hover"],
                        padding=10,
                        border_radius=8,
                    ),
                ], spacing=8),
                width=450,
            ),
            actions=[ft.TextButton("Entendido", on_click=lambda e: self._close(dlg))],
            bgcolor=COLORS["bg_card"],
        )
        self.page.overlay.append(dlg)
        dlg.open = True
        self.page.update()

    def _test_db_connection(self, e):
        """Probar conexión a la base de datos"""
        host = self.fields["db_host"].value
        port = self.fields["db_port"].value
        name = self.fields["db_name"].value
        user = self.fields["db_user"].value
        password = self.fields["db_password"].value
        
        try:
            from sqlalchemy import create_engine, text
            test_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
            test_engine = create_engine(test_url)
            
            with test_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            self.db_status.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["success"], size=16),
                ft.Text("Conexión exitosa", color=COLORS["success"], size=12),
            ], spacing=8)
            snackbar(self.page, f"Conexión exitosa a {host}:{port}/{name}", "success")
        except Exception as ex:
            self.db_status.content = ft.Row([
                ft.Icon(ft.Icons.ERROR, color=COLORS["danger"], size=16),
                ft.Text("Error de conexión", color=COLORS["danger"], size=12),
            ], spacing=8)
            snackbar(self.page, f"Error: {str(ex)[:100]}", "danger")
        
        self.page.update()

    def _save_db_config(self, e):
        """Guardar configuración de base de datos en archivo .env"""
        host = self.fields["db_host"].value
        port = self.fields["db_port"].value
        name = self.fields["db_name"].value
        user = self.fields["db_user"].value
        password = self.fields["db_password"].value
        
        # Primero probar la conexión
        try:
            from sqlalchemy import create_engine, text
            test_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"
            test_engine = create_engine(test_url)
            
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as ex:
            snackbar(self.page, f"No se puede conectar. Verifique los datos: {str(ex)[:80]}", "danger")
            return
        
        # Guardar en archivo .env
        try:
            from config import BASE_DIR
            env_path = BASE_DIR / ".env"
            
            # Leer archivo actual
            env_content = {}
            if env_path.exists():
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            env_content[key.strip()] = value.strip()
            
            # Actualizar valores de DB
            env_content["DB_HOST"] = host
            env_content["DB_PORT"] = port
            env_content["DB_NAME"] = name
            env_content["DB_USER"] = user
            env_content["DB_PASSWORD"] = password
            
            # Escribir archivo
            with open(env_path, "w") as f:
                f.write("# Base de datos MySQL\n")
                f.write(f"DB_HOST={env_content.get('DB_HOST', 'localhost')}\n")
                f.write(f"DB_PORT={env_content.get('DB_PORT', '3306')}\n")
                f.write(f"DB_NAME={env_content.get('DB_NAME', 'siigo_python')}\n")
                f.write(f"DB_USER={env_content.get('DB_USER', 'root')}\n")
                f.write(f"DB_PASSWORD={env_content.get('DB_PASSWORD', '')}\n")
                f.write("\n# Carpetas de monitoreo\n")
                f.write(f"WATCH_FOLDER={env_content.get('WATCH_FOLDER', r'D:\SIIWI01\DOCELECTRONICOS')}\n")
                f.write(f"PROCESSED_FOLDER={env_content.get('PROCESSED_FOLDER', r'D:\SIIWI01\DOCELECTRONICOS\procesados')}\n")
                f.write("\n# API DIAN\n")
                f.write(f"APIDIAN_URL={env_content.get('APIDIAN_URL', 'https://apidian.clipers.pro/api/ubl2.1')}\n")
            
            self.db_status.content = ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=COLORS["success"], size=16),
                ft.Text("Guardado - Reinicie la app", color=COLORS["success"], size=12),
            ], spacing=8)
            self.page.update()
            
            snackbar(self.page, "Configuración guardada. Reinicie la aplicación para aplicar cambios.", "success")
            
        except Exception as ex:
            snackbar(self.page, f"Error guardando configuración: {str(ex)}", "danger")

    def _build_certificate_tab(self) -> ft.Container:
        """Construir pestaña de certificado digital"""
        # Mostrar certificado actual si existe
        cert_status = ""
        if self.settings.certificate_path and os.path.exists(self.settings.certificate_path):
            cert_status = os.path.basename(self.settings.certificate_path)
        
        self.cert_file_display = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.VERIFIED_USER, color=COLORS["success"] if cert_status else COLORS["text_secondary"], size=20),
                ft.Text(
                    cert_status if cert_status else "Ningún archivo seleccionado",
                    color=COLORS["text_primary"],
                    size=13
                ),
            ], spacing=10),
            bgcolor=COLORS["bg_secondary"],
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
            border_radius=8,
            border=ft.border.all(1, COLORS["border"]),
        )
        
        self.fields["certificate_password"] = text_field(
            "Contraseña del Certificado",
            self.settings.certificate_password or "",
            password=True,
            width=300
        )
        
        # File picker para seleccionar certificado
        self.file_picker = ft.FilePicker(on_result=self._on_certificate_selected)
        self.page.overlay.append(self.file_picker)
        
        return ft.Container(
            content=ft.Column([
                section_title("Certificado Digital", "Certificado para firma electrónica (.p12 o .pfx)"),
                divider(),
                ft.Text("Certificado Digital (.p12 o .pfx)", color=COLORS["text_secondary"], size=13),
                self.cert_file_display,
                ft.Row([
                    button("Seleccionar Certificado", self._pick_certificate, icon=ft.Icons.UPLOAD_FILE),
                    button("Subir a ApiDian", self._upload_certificate, color="success", icon=ft.Icons.CLOUD_UPLOAD),
                ], spacing=12),
                ft.Text("Sube tu certificado digital en formato .p12 o .pfx", color=COLORS["text_secondary"], size=12),
                ft.Container(height=16),
                self.fields["certificate_password"],
            ], spacing=16),
            padding=24,
        )

    def _pick_certificate(self, e):
        """Abrir selector de archivo para certificado"""
        self.file_picker.pick_files(
            allowed_extensions=["p12", "pfx"],
            dialog_title="Seleccionar Certificado Digital",
        )

    def _on_certificate_selected(self, e: ft.FilePickerResultEvent):
        """Manejar selección de archivo de certificado"""
        if e.files and len(e.files) > 0:
            file = e.files[0]
            file_path = file.path
            
            # Leer el contenido del archivo inmediatamente
            try:
                with open(file_path, "rb") as f:
                    self.certificate_content = f.read()
                
                if len(self.certificate_content) == 0:
                    snackbar(self.page, "Error: El archivo está vacío", "danger")
                    return
                
                file_size = len(self.certificate_content) / 1024
                self.certificate_file = file_path
                self.certificate_filename = file.name
                
                # Actualizar display
                self.cert_file_display.content = ft.Row([
                    ft.Icon(ft.Icons.VERIFIED_USER, color=COLORS["success"], size=20),
                    ft.Text(file.name, color=COLORS["text_primary"], size=13),
                    ft.Text(f"({file_size:.1f} KB)", color=COLORS["text_secondary"], size=12),
                ], spacing=10)
                
                # Guardar ruta en settings
                session = get_session()
                s = session.query(Settings).first()
                s.certificate_path = file_path
                session.commit()
                session.close()
                
                self.page.update()
                snackbar(self.page, f"Certificado cargado: {file.name} ({file_size:.1f} KB)", "success")
                
            except Exception as ex:
                snackbar(self.page, f"Error leyendo archivo: {str(ex)}", "danger")
                self.certificate_content = None

    def _upload_certificate(self, e):
        """Subir certificado a ApiDian"""
        # Verificar que hay certificado cargado en memoria
        if not hasattr(self, 'certificate_content') or not self.certificate_content:
            # Intentar leer desde la ruta guardada
            cert_path = getattr(self, 'certificate_file', None) or self.settings.certificate_path
            if cert_path and os.path.exists(cert_path):
                try:
                    with open(cert_path, "rb") as f:
                        self.certificate_content = f.read()
                    if len(self.certificate_content) == 0:
                        snackbar(self.page, "Error: El certificado está vacío", "danger")
                        return
                except Exception as ex:
                    snackbar(self.page, f"Error leyendo certificado: {str(ex)}", "danger")
                    return
            else:
                snackbar(self.page, "Selecciona un certificado primero", "warning")
                return
        
        password = self.fields["certificate_password"].value
        if not password:
            snackbar(self.page, "Ingresa la contraseña del certificado", "warning")
            return
        
        # Guardar contraseña
        session = get_session()
        s = session.query(Settings).first()
        s.certificate_password = password
        session.commit()
        session.close()
        
        # Convertir a base64
        try:
            cert_base64 = base64.b64encode(self.certificate_content).decode("utf-8")
            # Debug: mostrar tamaño del base64
            print(f"Certificate base64 length: {len(cert_base64)}")
        except Exception as ex:
            snackbar(self.page, f"Error codificando certificado: {str(ex)}", "danger")
            return
        
        # Subir a ApiDian
        service = ApiDianService()
        result = service.upload_certificate(cert_base64, password)
        
        if result.get("success"):
            snackbar(self.page, "Certificado subido exitosamente a ApiDian", "success")
        else:
            error_msg = result.get("message", "Error desconocido")
            if "could not be read" in error_msg.lower():
                error_msg = "Contraseña incorrecta o certificado inválido"
            snackbar(self.page, f"Error: {error_msg}", "danger")

    def _save(self, e):
        session = get_session()
        s = session.query(Settings).first()
        s.type_document_identification_id = int(self.fields["type_document_identification_id"].value or 3)
        s.company_nit = self.fields["company_nit"].value
        s.company_dv = self.fields["company_dv"].value
        s.company_name = self.fields["company_name"].value
        s.merchant_registration = self.fields["merchant_registration"].value
        s.type_organization_id = int(self.fields["type_organization_id"].value or 2)
        s.type_regime_id = int(self.fields["type_regime_id"].value or 2)
        s.type_liability_id = int(self.fields["type_liability_id"].value or 117)
        s.department_id = int(self.fields["department_id"].value or 22)
        s.municipality_id = int(self.fields["municipality_id"].value or 520)
        s.company_address = self.fields["company_address"].value
        s.company_phone = self.fields["company_phone"].value
        s.company_email = self.fields["company_email"].value
        s.api_url = self.fields["api_url"].value
        s.api_token = self.fields["api_token"].value
        s.software_id = self.fields["software_id"].value
        s.software_pin = self.fields["software_pin"].value
        s.test_set_id = self.fields["test_set_id"].value
        s.type_environment_id = int(self.fields["type_environment_id"].value or 2)
        # Documento Soporte
        s.ds_software_id = self.fields["ds_software_id"].value
        s.ds_software_pin = self.fields["ds_software_pin"].value
        s.ds_test_set_id = self.fields["ds_test_set_id"].value
        # Correo
        s.mail_host = self.fields["mail_host"].value
        s.mail_port = int(self.fields["mail_port"].value or 587)
        s.mail_username = self.fields["mail_username"].value
        s.mail_password = self.fields["mail_password"].value
        s.mail_encryption = self.fields["mail_encryption"].value
        s.watch_folder = self.fields["watch_folder"].value
        s.processed_folder = self.fields["processed_folder"].value
        session.commit()
        session.close()
        snackbar(self.page, "Configuración guardada", "success")

    def _test_connection(self, e):
        service = ApiDianService()
        result = service.test_connection()
        if result.get("success"):
            snackbar(self.page, "Conexión exitosa", "success")
        else:
            snackbar(self.page, f"Error: {result.get('message', 'Sin conexión')}", "danger")

    def _configure_company(self, e):
        self._save(e)
        service = ApiDianService()
        result = service.configure_company()
        if result.get("success"):
            if result.get("token"):
                session = get_session()
                s = session.query(Settings).first()
                s.api_token = result["token"]
                session.commit()
                session.close()
                self.fields["api_token"].value = result["token"]
                self.page.update()
            snackbar(self.page, "Empresa configurada", "success")
        else:
            snackbar(self.page, f"Error: {result.get('message')}", "danger")

    def _configure_software(self, e):
        service = ApiDianService()
        result = service.configure_software()
        if result.get("success"):
            snackbar(self.page, "Software de facturación configurado", "success")
        else:
            snackbar(self.page, f"Error: {result.get('message')}", "danger")

    def _configure_software_ds(self, e):
        """Configurar software de Documento Soporte en ApiDian"""
        service = ApiDianService()
        result = service.configure_software_ds()
        if result.get("success"):
            snackbar(self.page, "Software de Documento Soporte configurado", "success")
        else:
            snackbar(self.page, f"Error: {result.get('message')}", "danger")
