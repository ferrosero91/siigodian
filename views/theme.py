"""Tema oscuro para la aplicación - Estilo Filament"""
import flet as ft

# Colores del tema (similar a Filament)
COLORS = {
    "bg_primary": "#111827",      # gray-900
    "bg_secondary": "#1f2937",    # gray-800
    "bg_card": "#1f2937",         # gray-800
    "bg_hover": "#374151",        # gray-700
    "bg_input": "#111827",        # gray-900
    "text_primary": "#f9fafb",    # gray-50
    "text_secondary": "#9ca3af",  # gray-400
    "border": "#374151",          # gray-700
    "border_focus": "#3b82f6",    # blue-500
    "primary": "#3b82f6",         # blue-500
    "success": "#10b981",         # emerald-500
    "warning": "#f59e0b",         # amber-500
    "danger": "#ef4444",          # red-500
    "info": "#06b6d4",            # cyan-500
}


def get_theme() -> ft.Theme:
    """Obtener tema de la aplicación"""
    return ft.Theme(
        color_scheme_seed=COLORS["primary"],
        color_scheme=ft.ColorScheme(
            primary=COLORS["primary"],
            on_primary="#ffffff",
            surface=COLORS["bg_secondary"],
            on_surface=COLORS["text_primary"],
            background=COLORS["bg_primary"],
            on_background=COLORS["text_primary"],
            error=COLORS["danger"],
        ),
    )


def card(content, **kwargs) -> ft.Container:
    """Crear tarjeta con estilo"""
    return ft.Container(
        content=content,
        bgcolor=COLORS["bg_card"],
        border_radius=12,
        padding=20,
        border=ft.border.all(1, COLORS["border"]),
        **kwargs
    )


def button(text: str, on_click=None, color: str = "primary", icon=None, disabled=False, **kwargs) -> ft.ElevatedButton:
    """Crear botón con estilo"""
    bg_color = COLORS.get(color, COLORS["primary"])
    return ft.ElevatedButton(
        text=text,
        icon=icon,
        on_click=on_click,
        bgcolor=bg_color if not disabled else COLORS["bg_hover"],
        color="#ffffff",
        disabled=disabled,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
        ),
        **kwargs
    )


def icon_button(icon, on_click=None, tooltip: str = "", color: str = "primary", **kwargs) -> ft.IconButton:
    """Crear botón de icono"""
    return ft.IconButton(
        icon=icon,
        on_click=on_click,
        tooltip=tooltip,
        icon_color=COLORS.get(color, COLORS["primary"]),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        **kwargs
    )


def text_field(label: str, value: str = "", password: bool = False, width: int = None, **kwargs) -> ft.TextField:
    """Crear campo de texto con estilo"""
    return ft.TextField(
        label=label,
        value=value,
        password=password,
        can_reveal_password=password,
        width=width,
        bgcolor=COLORS["bg_input"],
        border_color=COLORS["border"],
        focused_border_color=COLORS["border_focus"],
        label_style=ft.TextStyle(color=COLORS["text_secondary"], size=13),
        text_style=ft.TextStyle(color=COLORS["text_primary"], size=14),
        cursor_color=COLORS["primary"],
        border_radius=8,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=16),
        **kwargs
    )


def dropdown(label: str, value: str = "", options: list = None, width: int = None, on_change=None, **kwargs) -> ft.Dropdown:
    """Crear dropdown con estilo"""
    return ft.Dropdown(
        label=label,
        value=value,
        options=options or [],
        width=width,
        on_change=on_change,
        bgcolor=COLORS["bg_input"],
        border_color=COLORS["border"],
        focused_border_color=COLORS["border_focus"],
        label_style=ft.TextStyle(color=COLORS["text_secondary"], size=13),
        text_style=ft.TextStyle(color=COLORS["text_primary"], size=14),
        border_radius=8,
        content_padding=ft.padding.symmetric(horizontal=12, vertical=8),
        **kwargs
    )


def badge(text: str, color: str = "primary") -> ft.Container:
    """Crear badge/etiqueta"""
    bg_color = COLORS.get(color, COLORS["primary"])
    return ft.Container(
        content=ft.Text(text, size=11, color="#ffffff", weight=ft.FontWeight.W_600),
        bgcolor=bg_color,
        border_radius=6,
        padding=ft.padding.symmetric(horizontal=10, vertical=4),
    )


def status_badge(status: str) -> ft.Container:
    """Badge de estado"""
    colors = {
        "pending": "warning",
        "processing": "info",
        "sent": "success",
        "error": "danger",
        "rejected": "danger",
    }
    labels = {
        "pending": "Pendiente",
        "processing": "Procesando",
        "sent": "Procesado",
        "error": "Error",
        "rejected": "Rechazado",
    }
    return badge(labels.get(status, status), colors.get(status, "primary"))


def type_badge(doc_type: str) -> ft.Container:
    """Badge de tipo de documento"""
    colors = {
        "invoice": "primary",
        "credit_note": "warning",
        "debit_note": "info",
    }
    labels = {
        "invoice": "Factura",
        "credit_note": "Nota Crédito",
        "debit_note": "Nota Débito",
    }
    return badge(labels.get(doc_type, doc_type), colors.get(doc_type, "primary"))


def section_title(text: str, subtitle: str = None) -> ft.Column:
    """Título de sección"""
    controls = [
        ft.Text(text, size=18, weight=ft.FontWeight.W_600, color=COLORS["text_primary"])
    ]
    if subtitle:
        controls.append(
            ft.Text(subtitle, size=13, color=COLORS["text_secondary"])
        )
    return ft.Column(controls, spacing=4)


def divider() -> ft.Divider:
    """Divisor con estilo"""
    return ft.Divider(color=COLORS["border"], height=1, thickness=1)


def data_table_header(columns: list) -> ft.Container:
    """Header de tabla de datos"""
    return ft.Container(
        content=ft.Row(
            [ft.Text(col["label"], width=col.get("width"), weight=ft.FontWeight.W_600, 
                    color=COLORS["text_secondary"], size=12) for col in columns],
            spacing=10,
        ),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        bgcolor=COLORS["bg_secondary"],
        border_radius=ft.border_radius.only(top_left=8, top_right=8),
    )


def data_table_row(cells: list, on_click=None) -> ft.Container:
    """Fila de tabla de datos"""
    return ft.Container(
        content=ft.Row(cells, spacing=10),
        padding=ft.padding.symmetric(horizontal=16, vertical=12),
        bgcolor=COLORS["bg_card"],
        border=ft.border.only(bottom=ft.BorderSide(1, COLORS["border"])),
        on_hover=lambda e: _on_row_hover(e),
        on_click=on_click,
    )


def _on_row_hover(e):
    """Efecto hover en fila"""
    e.control.bgcolor = COLORS["bg_hover"] if e.data == "true" else COLORS["bg_card"]
    e.control.update()


def snackbar(page: ft.Page, message: str, color: str = "primary"):
    """Mostrar notificación"""
    page.snack_bar = ft.SnackBar(
        content=ft.Row([
            ft.Icon(
                ft.Icons.CHECK_CIRCLE if color == "success" else 
                ft.Icons.ERROR if color == "danger" else 
                ft.Icons.INFO,
                color="#ffffff",
                size=20,
            ),
            ft.Text(message, color="#ffffff", size=14),
        ], spacing=10),
        bgcolor=COLORS.get(color, COLORS["primary"]),
        behavior=ft.SnackBarBehavior.FLOATING,
        width=400,
        duration=3000,
    )
    page.snack_bar.open = True
    page.update()


def dialog(title: str, content, actions: list = None) -> ft.AlertDialog:
    """Crear diálogo con estilo"""
    return ft.AlertDialog(
        title=ft.Text(title, size=18, weight=ft.FontWeight.W_600),
        content=content,
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=12),
        bgcolor=COLORS["bg_card"],
    )
