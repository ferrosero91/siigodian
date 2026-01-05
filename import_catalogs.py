"""Script para importar catálogos desde los CSV"""
import os
import sys

# Ruta a los CSV dentro del proyecto
CSV_PATH = os.path.join(os.path.dirname(__file__), 'data', 'csv')

def read_csv(filename):
    """Leer archivo CSV (separado por tabs)"""
    filepath = os.path.join(CSV_PATH, filename)
    data = []
    encodings = ['utf-8', 'latin-1', 'cp1252']
    
    for encoding in encodings:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        parts = line.split('\t')
                        data.append(parts)
            break
        except UnicodeDecodeError:
            continue
    
    return data

def import_all():
    """Importar departamentos y municipios"""
    from database import get_session, Department, Municipality
    
    session = get_session()
    
    # Primero eliminar municipios (por la FK)
    print("Eliminando municipios existentes...")
    session.query(Municipality).delete()
    session.commit()
    
    # Luego eliminar departamentos
    print("Eliminando departamentos existentes...")
    session.query(Department).delete()
    session.commit()
    
    # Importar departamentos
    print("Importando departamentos...")
    dept_data = read_csv('departments.csv')
    for row in dept_data:
        if len(row) >= 3:
            dept = Department(
                id=int(row[0]),
                name=row[2],
                code=row[3] if len(row) > 3 else str(row[0])
            )
            session.add(dept)
    session.commit()
    dept_count = session.query(Department).count()
    print(f"  -> {dept_count} departamentos importados")
    
    # Importar municipios
    print("Importando municipios...")
    muni_data = read_csv('municipalities.csv')
    for row in muni_data:
        if len(row) >= 4:
            muni = Municipality(
                id=int(row[0]),
                department_id=int(row[1]),
                name=row[2].strip(),
                code=row[3],
                codefacturador=row[4] if len(row) > 4 else None
            )
            session.add(muni)
    session.commit()
    muni_count = session.query(Municipality).count()
    print(f"  -> {muni_count} municipios importados")
    
    session.close()
    return dept_count, muni_count

if __name__ == "__main__":
    print("=" * 50)
    print("Importando catálogos desde CSV del API DIAN")
    print("=" * 50)
    import_all()
    print("=" * 50)
    print("Importación completada!")
    print("=" * 50)
