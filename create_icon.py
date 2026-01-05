"""Script para crear el icono de la aplicación"""
from PIL import Image, ImageDraw

def create_icon():
    # Tamaños para el ICO
    sizes = [16, 32, 48, 64, 128, 256]
    images = []
    
    for size in sizes:
        # Crear imagen con fondo azul
        img = Image.new('RGBA', (size, size), (59, 130, 246, 255))
        draw = ImageDraw.Draw(img)
        
        margin = size // 8
        
        # Fondo del documento (blanco redondeado)
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=size // 10,
            fill=(255, 255, 255, 255)
        )
        
        # Líneas simulando texto
        line_margin = size // 5
        line_height = max(2, size // 14)
        line_spacing = max(4, size // 8)
        
        y = margin + line_margin
        for i in range(3):
            width_factor = 0.8 if i == 0 else (0.6 if i == 1 else 0.7)
            line_width = int((size - margin * 2 - line_margin) * width_factor)
            if y + line_height < size - margin - line_margin:
                draw.rounded_rectangle(
                    [margin + line_margin // 2, y, 
                     margin + line_margin // 2 + line_width, y + line_height],
                    radius=line_height // 2,
                    fill=(59, 130, 246, 180)
                )
            y += line_spacing
        
        # Círculo verde con check en esquina inferior derecha
        check_size = size // 3
        check_x = size - margin - check_size + margin // 2
        check_y = size - margin - check_size + margin // 2
        
        draw.ellipse(
            [check_x, check_y, check_x + check_size, check_y + check_size],
            fill=(34, 197, 94, 255)
        )
        
        images.append(img)
    
    # Guardar como ICO con todas las resoluciones
    images[-1].save(
        'icon.ico',
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=images[:-1]
    )
    print(f"Icono creado: icon.ico")

if __name__ == "__main__":
    create_icon()
