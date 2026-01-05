# Guía de Migración a Producción - Siigo DIAN

## Introducción

Esta guía detalla el proceso paso a paso para migrar el sistema de facturación electrónica desde el ambiente de **Habilitación (Pruebas)** al ambiente de **Producción** ante la DIAN.

---

## Requisitos Previos

Antes de iniciar el proceso de migración, asegúrese de cumplir con los siguientes requisitos:

### 1. Pruebas de Habilitación Completadas
- [ ] Haber enviado exitosamente las facturas de prueba requeridas por la DIAN
- [ ] Haber recibido respuesta exitosa de la DIAN para todos los documentos de prueba
- [ ] Verificar que el set de pruebas esté completo en el portal de la DIAN

### 2. Certificado Digital Vigente
- [ ] Tener un certificado digital válido (no vencido)
- [ ] El certificado debe estar registrado en la DIAN
- [ ] Conocer la contraseña del certificado

### 3. Resolución de Facturación
- [ ] Tener una resolución de facturación vigente para producción
- [ ] Conocer el número de resolución, prefijo, rango de numeración y fechas de vigencia
- [ ] Tener la clave técnica de la resolución (proporcionada por la DIAN)

### 4. Software Registrado
- [ ] Tener el ID del software registrado en la DIAN
- [ ] Conocer el PIN del software

---

## Proceso de Migración

### Paso 1: Verificar Estado en Portal DIAN

1. Ingrese al portal de la DIAN: https://catalogo-vpfe-hab.dian.gov.co/User/Login
2. Inicie sesión con su certificado digital
3. Vaya a **Facturador Electrónico** → **Configuración**
4. Verifique que el estado de habilitación sea **"Habilitado"**
5. Confirme que todas las pruebas del set de pruebas estén aprobadas

### Paso 2: Obtener Datos de Producción

En el portal de la DIAN, obtenga los siguientes datos para producción:

| Dato | Descripción | Dónde encontrarlo |
|------|-------------|-------------------|
| ID Software | Identificador único del software | Configuración → Software |
| PIN Software | Clave del software | Configuración → Software |
| Clave Técnica | Clave de la resolución | Configuración → Resoluciones |
| Resolución | Número de resolución | Configuración → Resoluciones |
| Prefijo | Prefijo de facturación | Configuración → Resoluciones |
| Rango | Desde - Hasta | Configuración → Resoluciones |

### Paso 3: Configurar Ambiente en ApiDian

El cambio de ambiente se realiza mediante el endpoint `PUT /config/environment`:

```json
{
    "type_environment_id": 1
}
```

**Valores de ambiente:**
- `1` = Producción
- `2` = Habilitación (Pruebas)

**Nota:** Al cambiar a producción, ApiDian automáticamente actualiza la URL del servicio web de la DIAN:
- Habilitación: `https://vpfe-hab.dian.gov.co/WcfDianCustomerServices.svc`
- Producción: `https://vpfe.dian.gov.co/WcfDianCustomerServices.svc`

### Paso 4: Configurar Resolución de Producción

Configure la resolución de producción en el sistema:

1. Abra la aplicación Siigo DIAN
2. Vaya a **Configuración** → **Resoluciones**
3. Agregue o edite la resolución con los datos de producción:
   - **Tipo de documento:** Factura de Venta (1)
   - **Prefijo:** El asignado por la DIAN
   - **Resolución:** Número de resolución
   - **Fecha de resolución:** Fecha de expedición
   - **Clave técnica:** La proporcionada por la DIAN (diferente a habilitación)
   - **Desde:** Número inicial del rango
   - **Hasta:** Número final del rango
   - **Fecha desde:** Inicio de vigencia
   - **Fecha hasta:** Fin de vigencia

### Paso 5: Actualizar Configuración del Software

1. Vaya a **Configuración** → **Software**
2. Actualice:
   - **ID Software:** El ID de producción
   - **PIN Software:** El PIN de producción
3. Guarde los cambios

### Paso 6: Verificar Certificado Digital

1. Vaya a **Configuración** → **Certificado**
2. Verifique que el certificado esté vigente
3. Si es necesario, suba nuevamente el certificado

### Paso 7: Cambiar Ambiente en la Aplicación

En la base de datos o configuración, actualice:

```sql
UPDATE settings SET type_environment_id = 1 WHERE id = 1;
```

O desde la aplicación, si tiene la opción de cambiar ambiente.

---

## Verificación Post-Migración

### Lista de Verificación

- [ ] Enviar una factura de prueba real (con valor mínimo)
- [ ] Verificar que la DIAN acepte el documento
- [ ] Confirmar que el CUFE se genere correctamente
- [ ] Verificar que el QR apunte a producción: `https://catalogo-vpfe.dian.gov.co/`
- [ ] Comprobar que el PDF se genere correctamente
- [ ] Verificar el envío de correo electrónico

### URLs de Verificación

| Ambiente | URL de Consulta |
|----------|-----------------|
| Habilitación | `https://catalogo-vpfe-hab.dian.gov.co/document/searchqr?documentkey={CUFE}` |
| Producción | `https://catalogo-vpfe.dian.gov.co/document/searchqr?documentkey={CUFE}` |

---

## Diferencias entre Ambientes

| Aspecto | Habilitación | Producción |
|---------|--------------|------------|
| URL DIAN | vpfe-hab.dian.gov.co | vpfe.dian.gov.co |
| URL QR | catalogo-vpfe-hab.dian.gov.co | catalogo-vpfe.dian.gov.co |
| Clave Técnica | Genérica de pruebas | Específica de la resolución |
| TestSetId | Requerido | No aplica |
| Documentos | No tienen validez fiscal | Validez fiscal completa |

---

## Solución de Problemas

### Error: "Documento rechazado por la DIAN"

1. Verifique que la resolución esté vigente
2. Confirme que el consecutivo esté dentro del rango autorizado
3. Revise que la clave técnica sea la correcta para producción

### Error: "Certificado no válido"

1. Verifique la fecha de vencimiento del certificado
2. Confirme que el certificado esté registrado en la DIAN
3. Suba nuevamente el certificado si es necesario

### Error: "Software no autorizado"

1. Verifique el ID y PIN del software
2. Confirme que el software esté habilitado en el portal DIAN
3. Reconfigure el software en ApiDian

---

## Contacto y Soporte

- **Portal DIAN:** https://www.dian.gov.co
- **Soporte Técnico DIAN:** 601 546 0055
- **Documentación ApiDian:** Consulte el archivo `ApiDianV2.1.postman_collection.json`

---

## Historial de Cambios

| Fecha | Versión | Descripción |
|-------|---------|-------------|
| 2024-12-29 | 1.0 | Documento inicial |

