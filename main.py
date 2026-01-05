"""
Siigo DIAN - Aplicación de Facturación Electrónica
Versión de escritorio con Python + Flet
"""
import flet as ft
from database import init_db
from views import DocumentsView, SettingsView, ResolutionsView, CustomersView, ProductsView, PurchasesView, COLORS, get_theme


def main(page: ft.Page):
    """Función principal de la aplicación"""
    
    # Configuración de la página
    page.title = "Siigo DIAN - Facturación Electrónica"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = get_theme()
    page.bgcolor = COLORS["bg_primary"]
    page.padding = 0
    page.window.width = 1400
    page.window.height = 800
    page.window.min_width = 1000
    page.window.min_height = 600
    
    # Inicializar base de datos
    init_db()
    
    # Vistas
    documents_view = DocumentsView(page)
    settings_view = SettingsView(page)
    resolutions_view = ResolutionsView(page)
    customers_view = CustomersView(page)
    products_view = ProductsView(page)
    purchases_view = PurchasesView(page)
    
    # Contenedor principal
    content_area = ft.Container(expand=True)
    
    # Navbar dinámico para documentos
    docs_navbar = ft.Container(
        content=documents_view.build_navbar(),
        visible=True,
        expand=True,
    )
    
    def change_view(index: int):
        """Cambiar vista según el índice del menú"""
        if index == 0:
            content_area.content = documents_view.build()
            docs_navbar.visible = True
        elif index == 1:
            content_area.content = purchases_view.build()
            docs_navbar.visible = False
        elif index == 2:
            content_area.content = customers_view.build()
            docs_navbar.visible = False
        elif index == 3:
            content_area.content = products_view.build()
            docs_navbar.visible = False
        elif index == 4:
            content_area.content = resolutions_view.build()
            docs_navbar.visible = False
        elif index == 5:
            content_area.content = settings_view.build()
            docs_navbar.visible = False
        page.update()
    
    # Navegación lateral
    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        min_extended_width=200,
        bgcolor=COLORS["bg_secondary"],
        indicator_color=COLORS["primary"],
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DESCRIPTION_OUTLINED,
                selected_icon=ft.Icons.DESCRIPTION,
                label="Documentos",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SHOPPING_CART_OUTLINED,
                selected_icon=ft.Icons.SHOPPING_CART,
                label="Compras",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PEOPLE_OUTLINED,
                selected_icon=ft.Icons.PEOPLE,
                label="Clientes",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.INVENTORY_2_OUTLINED,
                selected_icon=ft.Icons.INVENTORY_2,
                label="Productos",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                selected_icon=ft.Icons.RECEIPT_LONG,
                label="Resoluciones",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Configuración",
            ),
        ],
        on_change=lambda e: change_view(e.control.selected_index),
    )
    
    # Header con navbar de documentos integrado
    header = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.RECEIPT_LONG, color=COLORS["primary"], size=28),
            ft.Text(
                "Siigo DIAN",
                size=20,
                weight=ft.FontWeight.BOLD,
                color=COLORS["text_primary"],
            ),
            ft.Container(width=20),
            docs_navbar,
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        bgcolor=COLORS["bg_secondary"],
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
    )
    
    # Layout principal
    page.add(
        ft.Column([
            header,
            ft.Row([
                nav_rail,
                ft.VerticalDivider(width=1, color=COLORS["border"]),
                content_area,
            ], expand=True, spacing=0),
        ], expand=True, spacing=0)
    )
    
    # Cargar vista inicial
    change_view(0)


if __name__ == "__main__":
    ft.app(target=main)
